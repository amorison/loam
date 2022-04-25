"""Main classes to define your configuration."""

from __future__ import annotations

from dataclasses import dataclass, asdict, fields, field, Field
from os import PathLike
from pathlib import Path
from typing import (
    get_type_hints,
    TypeVar, Generic, Callable, Optional, Dict, Any, Type, Union, Mapping
)

import toml

T = TypeVar("T")


@dataclass(frozen=True)
class Entry(Generic[T]):
    """Metadata of configuration options.

    Attributes:
        doc: short description of the option.
        in_file: whether the option can be set in the config file.
        in_cli: whether the option is a command line argument.
        cli_short: short version of the command line argument.
        cli_kwargs: keyword arguments fed to
            :meth:`argparse.ArgumentParser.add_argument` during the
            construction of the command line arguments parser.
        cli_zsh_comprule: completion rule for ZSH shell.
    """

    doc: str = ""
    from_str: Optional[Callable[[str], T]] = None
    to_str: Optional[Callable[[T], str]] = None
    in_file: bool = True
    in_cli: bool = True
    cli_short: Optional[str] = None
    cli_kwargs: Dict[str, Any] = field(default_factory=dict)
    cli_zsh_comprule: Optional[str] = ''

    def with_str(self, val_as_str: str) -> T:
        """Set default value from a string representation.

        This uses :attr:`from_str`.  Note that the call itself is embedded in a
        factory function to avoid issues if the generated value is mutable.
        """
        if self.from_str is None:
            raise ValueError("Need `from_str` to call with_str")
        func = self.from_str  # for mypy to see func is not None here
        return self.with_factory(lambda: func(val_as_str))

    def with_val(self, val: T) -> T:
        """Set default value.

        Use :meth:`with_factory` or :meth:`with_str` if the value is mutable.
        """
        return field(default=val, metadata=dict(loam_entry=self))

    def with_factory(self, func: Callable[[], T]) -> T:
        """Set default value from a factory function.

        This is useful with the value is mutable.
        """
        return field(default_factory=func, metadata=dict(loam_entry=self))


@dataclass(frozen=True)
class _Meta(Generic[T]):
    """Group several metadata."""

    fld: Field[T]
    entry: Entry[T]
    type_hint: Type[T]


@dataclass
class Section:
    """Base class for a configuration section.

    This implements :meth:`__post_init__`. If your subclass also implement
    it, please call the parent implementation.
    """

    @classmethod
    def _type_hints(cls) -> Dict[str, Any]:
        return get_type_hints(cls)

    def __post_init__(self) -> None:
        self._loam_meta: Dict[str, _Meta] = {}
        thints = self._type_hints()
        for fld in fields(self):
            meta = fld.metadata.get("loam_entry", Entry())
            thint = thints[fld.name]
            if not isinstance(thint, type):
                thint = object
            self._loam_meta[fld.name] = _Meta(fld, meta, thint)

            current_val = getattr(self, fld.name)
            if (not issubclass(thint, str)) and isinstance(current_val, str):
                self.set_from_str(fld.name, current_val)
                current_val = getattr(self, fld.name)
            if not isinstance(current_val, thint):
                typ = type(current_val)
                raise TypeError(
                    f"Expected a {thint} for {fld.name}, received a {typ}.")

    def set_from_str(self, field_name: str, value_as_str: str) -> None:
        """Set an option from the string representation of the value.

        This uses :meth:`Entry.from_str` to parse the given string, and
        fall back on the type annotation if it resolves to a class.
        """
        meta = self._loam_meta[field_name]
        if issubclass(meta.type_hint, str):
            value = value_as_str
        elif meta.entry.from_str is not None:
            value = meta.entry.from_str(value_as_str)
        else:
            try:
                value = meta.type_hint(value_as_str)
            except TypeError:
                raise ValueError(
                    f"Please specify a `from_str` for {field_name}.")
        setattr(self, field_name, value)


TConfig = TypeVar("TConfig", bound="Config")


@dataclass
class Config:
    """Base class for a full configuration."""

    @classmethod
    def default(cls: Type[TConfig]) -> TConfig:
        """Create a configuration with default values."""
        return cls.from_dict({})

    @classmethod
    def from_file(cls: Type[TConfig], path: Union[str, PathLike]) -> TConfig:
        """Read configuration from toml file."""
        pars = toml.load(Path(path))
        return cls.from_dict(pars)

    @classmethod
    def _type_hints(cls) -> Dict[str, Any]:
        return get_type_hints(cls)

    @classmethod
    def from_dict(
        cls: Type[TConfig], options: Mapping[str, Mapping[str, Any]]
    ) -> TConfig:
        """Create configuration from a dictionary."""
        thints = cls._type_hints()
        sections = {}
        for fld in fields(cls):
            thint = thints[fld.name]
            if not (isinstance(thint, type) and issubclass(thint, Section)):
                raise TypeError(
                    f"Could not resolve type hint of {fld.name} to a Section "
                    f"(got {thint})")
            section_dict = options.get(fld.name, {})
            sections[fld.name] = thint(**section_dict)
        return cls(**sections)

    def to_file(self, path: Union[str, PathLike]) -> None:
        """Write configuration in toml file."""
        dct = asdict(self)
        for sec_name, sec_dict in dct.items():
            for fld in fields(getattr(self, sec_name)):
                entry: Entry = fld.metadata.get("loam_entry", Entry())
                if entry.to_str is not None:
                    sec_dict[fld.name] = entry.to_str(sec_dict[fld.name])
        with Path(path).open('w') as pf:
            toml.dump(dct, pf)
