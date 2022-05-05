"""Define entries for common containers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Generic, TypeVar, Callable, Optional, Iterable, Tuple

from .base import Entry


T = TypeVar("T")
U = TypeVar("U")


@dataclass(frozen=True)
class TupleEntry(Generic[T]):
    """Represent a tuple[T, ...] entry.

    It is able to:

    - parse a TOML array [elt_a, elt_b, elt_c] into a tuple[T, ...] by feeding
      each element to :attr:`inner_from_toml`.
    - parse a string into a tuple[T, ...] by splitting the string with
      :attr:`str_sep`, stripping each substrings, and feeding those to
      :attr:`inner_from_toml` (which therefore should be able to parse strings
      into T). Set :attr:`str_sep` to "" to split on whitespaces, and set it to
      None to raise a TypeError when attempting to parse a string into a tuple.
    - dump the tuple as a TOML array using `inner_to_toml` to convert each
      element into a type with a TOML representation.
    - see :meth:`entry` for comments on the CLI capabilities.

    Note that you don't have to specify `inner_to_toml` if the inner type is
    already representable as a toml object.
    """

    inner_from_toml: Callable[[object], T]
    inner_to_toml: Optional[Callable[[T], object]] = None
    str_sep: Optional[str] = ","

    @staticmethod
    def wrapping(
        tuple_entry: TupleEntry[U], str_sep: Optional[str]
    ) -> TupleEntry[Tuple[U, ...]]:
        """Produce a tuple entry wrapping another one.

        It is the user responsibility to check that separators are different in
        nested TupleEntries.
        """
        return TupleEntry(
            inner_from_toml=tuple_entry.from_toml,
            inner_to_toml=tuple_entry.to_toml,
            str_sep=str_sep,
        )

    def entry(self, default: Iterable[T], doc: str = "", in_file: bool = True,
              in_cli_as: Optional[str] = "list",
              cli_short: Optional[str] = None,
              cli_zsh_comprule: Optional[str] = "") -> Tuple[T, ...]:
        """Produce a :class:`dataclasses.Field` with desired options.

        See :class:`~loam.base.Entry` for an explanation on the parameters.
        The `in_cli_as` option controls the CLI arguments, it can be either of:

        - "list" (the default), meaning the CLI argument accepts several
          values, e.g ``--arg elt_a elt_b elt_c``;
        - "str", meaning the CLI argument accepts one string value, e.g.
          ``--arg "elt_a, elt_b, elt_c"``;
        - `None`, meaning the entry is not part of the CLI.
        """
        cli_kwargs = {}
        if in_cli_as is not None:
            if in_cli_as == "list":
                cli_kwargs = {"nargs": "*"}
            elif in_cli_as == "str":
                cli_kwargs = {"nargs": "?", "const": ""}
            else:
                raise ValueError(
                    "in_cli_as should be one of 'list', 'str', or None;"
                    f" {in_cli_as} received")
        return Entry(
            val=tuple(default),
            doc=doc,
            from_toml=self.from_toml,
            to_toml=self.to_toml,
            in_file=in_file,
            in_cli=in_cli_as is not None,
            cli_short=cli_short,
            cli_kwargs=cli_kwargs,
            cli_zsh_comprule=cli_zsh_comprule,
        ).field()

    def from_toml(self, obj: object) -> Tuple[T, ...]:
        """Build a tuple from a TOML object."""
        if isinstance(obj, str):
            sep = self.str_sep
            if sep is None:
                raise TypeError(
                    "Cannot parse str into a Tuple as str_sep is None")
            sep = sep if sep != "" else None
            obj = tuple(map(str.strip, obj.split(sep)))
        if isinstance(obj, (list, tuple)):
            return tuple(map(self.inner_from_toml, obj))
        raise TypeError(
            f"obj should be a str, tuple, or list; got a {obj.__class__}")

    def to_toml(self, val: Tuple[T, ...]) -> Tuple[object, ...]:
        """Transform into a TOML array."""
        if self.inner_to_toml is None:
            return val
        return tuple(map(self.inner_to_toml, val))


@dataclass
class MaybeEntry(Generic[T]):
    """Represent an Optional[T] entry."""

    inner_from_toml: Callable[[object], T]
    inner_to_toml: Optional[Callable[[T], object]] = None
    none_to_toml: object = ""

    def entry(self, default: Optional[T], doc: str = "", in_file: bool = True,
              in_cli_as: Optional[str] = "optional",
              cli_short: Optional[str] = None,
              cli_zsh_comprule: Optional[str] = "") -> Optional[T]:
        """Produce a :class:`dataclasses.Field` with desired options.

        See :class:`~loam.base.Entry` for an explanation on the parameters.
        The `in_cli_as` option controls the CLI argument, it can be either of:

        - "optional" (the default), meaning the CLI argument can be fed an
          empty value, resulting in None, e.g ``--arg``;
        - "mandatory", meaning the CLI argument has to be fed a value, e.g.
          ``--arg 42"``;
        - `None`, meaning the entry is not part of the CLI.
        """
        cli_kwargs = {}
        if in_cli_as is not None:
            if in_cli_as == "optional":
                cli_kwargs = {"nargs": "?", "const": None}
            elif in_cli_as != "mandatory":
                raise ValueError(
                    "in_cli_as should be one of 'optional', 'mandatory', "
                    f"or None; {in_cli_as} received")
        return Entry(
            val_factory=lambda: default,
            doc=doc,
            from_toml=self.from_toml,
            to_toml=self.to_toml,
            in_file=in_file,
            in_cli=in_cli_as is not None,
            cli_short=cli_short,
            cli_kwargs=cli_kwargs,
            cli_zsh_comprule=cli_zsh_comprule,
        ).field()

    def from_toml(self, obj: object) -> Optional[T]:
        """Build an Optional[T] from a TOML object."""
        if obj is None or self.none_to_toml == obj:
            return None
        return self.inner_from_toml(obj)

    def to_toml(self, val: Optional[T]) -> object:
        """Transform into a TOML object."""
        if val is None:
            return self.none_to_toml
        if self.inner_to_toml is not None:
            return self.inner_to_toml(val)
        return val
