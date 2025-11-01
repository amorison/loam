"""Main classes to define your configuration."""

from __future__ import annotations

from collections.abc import Mapping
from contextlib import AbstractContextManager
from dataclasses import Field, dataclass, field, fields
from os import PathLike
from pathlib import Path
from typing import (
    Any,
    Callable,
    Generic,
    TypeVar,
    get_type_hints,
)

import toml

from . import _internal

T = TypeVar("T")


@dataclass(frozen=True)
class Entry(Generic[T]):
    """Metadata of configuration options.

    Attributes:
        val: default value. Use `val_toml` or `val_factory` instead
            if it is mutable.
        val_toml: default value as a TOML value. `from_toml` is required.
            The call to the latter is wrapped in a function to avoid issues if
            the obtained value is mutable.
        val_factory: default value wrapped in a function, this is useful if the
            default value is mutable. This can be used to set a default value
            of `None`: `val_factory=lambda: None`.
        doc: short description of the option.
        from_toml: function to cast a value that can be represented as a TOML
            value to the type of the entry. When set, this is always called
            when reading a TOML file and command line arguments. Make sure you
            implement all the cases you want to support and raise a `TypeError`
            in other cases.
        to_toml: function to cast the entry to a type that can be represented
            as a TOML value. This is called when writing
            [`ConfigBase`][loam.base.ConfigBase] instances to a TOML file via
            [`ConfigBase.to_file_`][loam.base.ConfigBase.to_file_].
        in_file: whether the option can be set in the config file.
        in_cli: whether the option is a command line argument.
        cli_short: short version of the command line argument.
        cli_kwargs: keyword arguments fed to
            `argparse.ArgumentParser.add_argument` during the
            construction of the command line arguments parser.
        cli_zsh_comprule: completion rule for ZSH shell.
    """

    val: T | None = None
    val_toml: str | None = None
    val_factory: Callable[[], T] | None = None
    doc: str = ""
    from_toml: Callable[[object], T] | None = None
    to_toml: Callable[[T], object] | None = None
    in_file: bool = True
    in_cli: bool = True
    cli_short: str | None = None
    cli_kwargs: dict[str, Any] = field(default_factory=dict)
    cli_zsh_comprule: str | None = ""

    def field(self) -> T:
        """Produce a `dataclasses.Field` from the entry."""
        non_none_cout = (
            int(self.val is not None)
            + int(self.val_toml is not None)
            + int(self.val_factory is not None)
        )
        if non_none_cout != 1:
            raise ValueError(
                "Exactly one of val, val_toml, and val_factory should be set."
            )

        if self.val is not None:
            return field(default=self.val, metadata=dict(loam_entry=self))
        if self.val_factory is not None:
            func = self.val_factory
        else:
            if self.from_toml is None:
                raise ValueError("Need `from_toml` to use val_toml")

            def func() -> T:
                # TYPE SAFETY: previous checks ensure this is valid
                return self.from_toml(self.val_toml)  # type: ignore

        return field(default_factory=func, metadata=dict(loam_entry=self))


def entry(
    val: T | None = None,
    val_toml: str | None = None,
    val_factory: Callable[[], T] | None = None,
    doc: str = "",
    from_toml: Callable[[object], T] | None = None,
    to_toml: Callable[[T], object] | None = None,
    in_file: bool = True,
    in_cli: bool = True,
    cli_short: str | None = None,
    cli_kwargs: dict[str, Any] | None = None,
    cli_zsh_comprule: str | None = "",
) -> T:
    """Shorthand notation for `Entry(...).field()`."""
    if cli_kwargs is None:
        cli_kwargs = {}
    return Entry(
        val=val,
        val_toml=val_toml,
        val_factory=val_factory,
        doc=doc,
        from_toml=from_toml,
        to_toml=to_toml,
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
        fld: `dataclasses.Field` object from the underlying metadata.
        entry: the metadata from the loam API.
        type_hint: type hint resolved as a class. If the type hint could not
            be resolved as a class, this is merely `object`.
    """

    fld: Field[T]
    entry: Entry[T]
    type_hint: type[T]


@dataclass
class Section:
    """Base class for a configuration section.

    This implements `__post_init__`. If your subclass also implement
    it, please call the parent implementation.
    """

    @classmethod
    def _type_hints(cls) -> dict[str, Any]:
        return get_type_hints(cls)

    def __post_init__(self) -> None:
        self._loam_meta: dict[str, Meta] = {}
        thints = self._type_hints()
        for fld in fields(self):
            meta = fld.metadata.get("loam_entry", Entry())
            thint = thints[fld.name]
            if not isinstance(thint, type):
                thint = object
            self._loam_meta[fld.name] = Meta(fld, meta, thint)
            current_val = getattr(self, fld.name)
            if not isinstance(current_val, thint):
                self.cast_and_set_(fld.name, current_val)

    def meta_(self, entry_name: str) -> Meta:
        """Metadata for the given entry name."""
        return self._loam_meta[entry_name]

    def cast_and_set_(self, field_name: str, value_to_cast: object) -> None:
        """Set an option from the string representation of the value.

        This uses `Entry.from_toml` (if present) to cast the given value.
        If `Entry.from_toml` is not present and the type of
        `value_to_cast` do not match the type hint, this calls the type hint to
        attempt a cast. This should only be used when setting an option to a
        value whose type cannot be controlled. Wherever possible, directly set
        the option value with the correct type instead of calling this method.
        """
        meta = self._loam_meta[field_name]
        if meta.entry.from_toml is not None:
            value = meta.entry.from_toml(value_to_cast)
        elif not isinstance(value_to_cast, meta.type_hint):
            try:
                value = meta.type_hint(value_to_cast)
            except Exception:
                raise TypeError(
                    f"Couldn't cast {value_to_cast!r} to a {meta.type_hint}, "
                    f"you might need to specify `from_toml` for {field_name}."
                )
        else:
            value = value_to_cast
        setattr(self, field_name, value)

    def context_(self, **options: Any) -> AbstractContextManager[None]:
        """Enter a context with locally changed option values.

        This context is reusable but not reentrant.
        """
        return _internal.SectionContext(self, options)

    def update_from_dict_(self, options: Mapping[str, object]) -> None:
        """Update options from a mapping, casting values as needed."""
        for opt, val in options.items():
            self.cast_and_set_(opt, val)


TConfig = TypeVar("TConfig", bound="ConfigBase")


@dataclass
class ConfigBase:
    """Base class for a full configuration."""

    @classmethod
    def _type_hints(cls) -> dict[str, Any]:
        return get_type_hints(cls)

    @classmethod
    def default_(cls: type[TConfig]) -> TConfig:
        """Create a configuration with default values."""
        thints = cls._type_hints()
        sections = {}
        for fld in fields(cls):
            thint = thints[fld.name]
            if not (isinstance(thint, type) and issubclass(thint, Section)):
                raise TypeError(
                    f"Could not resolve type hint of {fld.name} to a Section "
                    f"(got {thint})"
                )
            sections[fld.name] = thint()
        return cls(**sections)

    def update_from_file_(self, path: str | PathLike) -> None:
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

    def update_from_dict_(self, options: Mapping[str, Mapping[str, Any]]) -> None:
        """Update configuration from a dictionary."""
        for sec, opts in options.items():
            section: Section = getattr(self, sec)
            section.update_from_dict_(opts)

    def to_file_(self, path: str | PathLike, exist_ok: bool = True) -> None:
        """Write configuration in toml file."""
        path = Path(path)
        if not exist_ok and path.is_file():
            raise RuntimeError(f"{path} already exists")
        path.parent.mkdir(parents=True, exist_ok=True)
        sections = fields(self)
        to_dump: dict[str, dict[str, Any]] = {}
        for sec in sections:
            to_dump[sec.name] = {}
            section: Section = getattr(self, sec.name)
            for fld in fields(section):
                entry = section.meta_(fld.name).entry
                if not entry.in_file:
                    continue
                value = getattr(section, fld.name)
                if entry.to_toml is not None:
                    value = entry.to_toml(value)
                to_dump[sec.name][fld.name] = value
            if not to_dump[sec.name]:
                del to_dump[sec.name]
        with path.open("w") as pf:
            toml.dump(to_dump, pf)
