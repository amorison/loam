"""Main classes to define your configuration."""

from __future__ import annotations

from dataclasses import dataclass, asdict, fields, field, Field
from os import PathLike
from pathlib import Path
from typing import (
    get_type_hints,
    TypeVar, Generic, Callable, Optional, Dict, Any, Type, Union, Mapping,
    ContextManager
)

import toml

from . import _internal

T = TypeVar("T")


@dataclass(frozen=True)
class Entry(Generic[T]):
    """Metadata of configuration options.

    Attributes:
        val: default value. Use :attr:`val_str` or :attr:`val_factory` instead
            if it is mutable.
        val_str: default value from a string representation. This requires
            :attr:`from_str`. The call to the latter is wrapped in a function
            to avoid issues if the obtained value is mutable.
        val_factory: default value wrapped in a function, this is useful if the
            default value is mutable. This can be used to set a default value
            of `None`: `val_factory=lambda: None`.
        doc: short description of the option.
        in_file: whether the option can be set in the config file.
        in_cli: whether the option is a command line argument.
        cli_short: short version of the command line argument.
        cli_kwargs: keyword arguments fed to
            :meth:`argparse.ArgumentParser.add_argument` during the
            construction of the command line arguments parser.
        cli_zsh_comprule: completion rule for ZSH shell.
    """

    val: Optional[T] = None
    val_str: Optional[str] = None
    val_factory: Optional[Callable[[], T]] = None
    doc: str = ""
    from_str: Optional[Callable[[str], T]] = None
    to_str: Optional[Callable[[T], str]] = None
    in_file: bool = True
    in_cli: bool = True
    cli_short: Optional[str] = None
    cli_kwargs: Dict[str, Any] = field(default_factory=dict)
    cli_zsh_comprule: Optional[str] = ''

    def field(self) -> T:
        """Produce a :class:`dataclasses.Field` from the entry."""
        non_none_cout = (int(self.val is not None) +
                         int(self.val_str is not None) +
                         int(self.val_factory is not None))
        if non_none_cout != 1:
            raise ValueError(
                "Exactly one of val, val_str, and val_factory should be set.")

        if self.val is not None:
            return field(default=self.val, metadata=dict(loam_entry=self))
        if self.val_factory is not None:
            func = self.val_factory
        else:
            if self.from_str is None:
                raise ValueError("Need `from_str` to use val_str")

            def func() -> T:
                # TYPE SAFETY: previous checks ensure this is valid
                return self.from_str(self.val_str)  # type: ignore

        return field(default_factory=func, metadata=dict(loam_entry=self))


def entry(
    val: Optional[T] = None,
    val_str: Optional[str] = None,
    val_factory: Optional[Callable[[], T]] = None,
    doc: str = "",
    from_str: Optional[Callable[[str], T]] = None,
    to_str: Optional[Callable[[T], str]] = None,
    in_file: bool = True,
    in_cli: bool = True,
    cli_short: Optional[str] = None,
    cli_kwargs: Dict[str, Any] = None,
    cli_zsh_comprule: Optional[str] = '',
) -> T:
    """Build Entry(...).field()."""
    if cli_kwargs is None:
        cli_kwargs = {}
    return Entry(
        val=val,
        val_str=val_str,
        val_factory=val_factory,
        doc=doc,
        from_str=from_str,
        to_str=to_str,
        in_file=in_file,
        in_cli=in_cli,
        cli_short=cli_short,
        cli_kwargs=cli_kwargs,
        cli_zsh_comprule=cli_zsh_comprule,
    ).field()


@dataclass(frozen=True)
class Meta(Generic[T]):
    """Group several metadata of configuration entry.

    Attributes:
        fld: :class:`dataclasses.Field` object from the underlying metadata.
        entry: the metadata from the loam API.
        type_hint: type hint resolved as a class. If the type hint could not
            be resolved as a class, this is merely :class:`object`.
    """

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
        self._loam_meta: Dict[str, Meta] = {}
        thints = self._type_hints()
        for fld in fields(self):
            meta = fld.metadata.get("loam_entry", Entry())
            thint = thints[fld.name]
            if not isinstance(thint, type):
                thint = object
            self._loam_meta[fld.name] = Meta(fld, meta, thint)
            current_val = getattr(self, fld.name)
            if isinstance(current_val, str) or not isinstance(current_val,
                                                              thint):
                self.set_safe_(fld.name, current_val)

    def meta_(self, entry_name: str) -> Meta:
        """Metadata for the given entry name."""
        return self._loam_meta[entry_name]

    def set_safe_(self, entry_name: str, value: Any) -> None:
        """Set an option from a value or a string.

        This method is only meant as a convenience to manipulate
        :class:`Section` instances in a dynamic way.  It parses strings if
        necessary and raises `TypeError` when the type can be determined to be
        incorrect.  When possible, either prefer directly setting the attribute
        or calling :meth:`set_from_str_` as those can be statically checked.
        """
        if isinstance(value, str):
            self.set_from_str_(entry_name, value)
        else:
            typ = self.meta_(entry_name).type_hint
            if isinstance(value, typ):
                setattr(self, entry_name, value)
            else:
                typg = type(value)
                raise TypeError(
                    f"Expected a {typ} for {entry_name}, received a {typg}.")

    def set_from_str_(self, field_name: str, value_as_str: str) -> None:
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

    def context_(self, **options: Any) -> ContextManager[None]:
        """Enter a context with locally changed option values.

        This context is reusable but not reentrant.
        """
        return _internal.SectionContext(self, options)

    def update_from_dict_(self, options: Mapping[str, Any]) -> None:
        """Update options from a mapping, parsing str as needed."""
        for opt, val in options.items():
            self.set_safe_(opt, val)


TConfig = TypeVar("TConfig", bound="ConfigBase")


@dataclass
class ConfigBase:
    """Base class for a full configuration."""

    @classmethod
    def _type_hints(cls) -> Dict[str, Any]:
        return get_type_hints(cls)

    @classmethod
    def default_(cls: Type[TConfig]) -> TConfig:
        """Create a configuration with default values."""
        thints = cls._type_hints()
        sections = {}
        for fld in fields(cls):
            thint = thints[fld.name]
            if not (isinstance(thint, type) and issubclass(thint, Section)):
                raise TypeError(
                    f"Could not resolve type hint of {fld.name} to a Section "
                    f"(got {thint})")
            sections[fld.name] = thint()
        return cls(**sections)

    def update_from_file_(self, path: Union[str, PathLike]) -> None:
        """Update configuration from toml file."""
        pars = toml.load(Path(path))
        # only keep entries for which in_file is True
        pars = {
            sec_name: {
                opt: val
                for opt, val in section.items()
                if getattr(self, sec_name).meta_(opt).entry.in_file
            }
            for sec_name, section in pars.items()
        }
        self.update_from_dict_(pars)

    def update_from_dict_(
        self, options: Mapping[str, Mapping[str, Any]]
    ) -> None:
        """Update configuration from a dictionary."""
        for sec, opts in options.items():
            section: Section = getattr(self, sec)
            section.update_from_dict_(opts)

    def to_file_(
        self, path: Union[str, PathLike], exist_ok: bool = True
    ) -> None:
        """Write configuration in toml file."""
        path = Path(path)
        if not exist_ok and path.is_file():
            raise RuntimeError(f"{path} already exists")
        path.parent.mkdir(parents=True, exist_ok=True)
        dct = asdict(self)
        to_dump: Dict[str, Dict[str, Any]] = {}
        for sec_name, sec_dict in dct.items():
            to_dump[sec_name] = {}
            section: Section = getattr(self, sec_name)
            for fld in fields(section):
                entry = section.meta_(fld.name).entry
                if not entry.in_file:
                    continue
                value = sec_dict[fld.name]
                if entry.to_str is not None:
                    value = entry.to_str(value)
                to_dump[sec_name][fld.name] = value
            if not to_dump[sec_name]:
                del to_dump[sec_name]
        with path.open('w') as pf:
            toml.dump(to_dump, pf)
