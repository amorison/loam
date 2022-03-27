"""Parsers for your CLI arguments.

These functions can be used as the `type` argument in
:attr:`~loam.manager.ConfOpt.cmd_kwargs`.
"""

from __future__ import annotations
import typing

if typing.TYPE_CHECKING:
    from typing import Union, Callable, TypeVar, Tuple
    T = TypeVar('T')


def strict_slice_parser(arg: str) -> slice:
    """Parse a string into a slice.

    Note that this errors out on a single integer with no `:`.  If you
    want to treat a single integer as a slice from 0 to that value, see
    :func:`slice_parser`.  To treat a single integer as an integer, see
    :func:`slice_or_int`.
    """
    soi = slice_or_int_parser(arg)
    if isinstance(soi, int):
        raise ValueError(f"{arg} is an invalid slice")
    return soi


def slice_parser(arg: str) -> slice:
    """Parse a string into a slice.

    Note that this treats a single integer as a slice from 0 to that
    value.  To error out on a single integer, use :func:`strict_slice_parser`.
    To parse it as an integer, use :func:`slice_or_int_parser`.
    """
    soi = slice_or_int_parser(arg)
    if isinstance(soi, int):
        return slice(soi)
    return soi


def slice_or_int_parser(arg: str) -> Union[slice, int]:
    """Parse a string into a slice.

    Note that this treats a single integer as an integer value.  To error out
    on a single integer, use :func:`strict_slice_parser`.  To parse it as a
    slice, use :func:`slice_parser`.
    """
    if ':' in arg:
        idxs = arg.split(':')
        if len(idxs) > 3:
            raise ValueError(f'{arg} is an invalid slice')
        slice_parts = [int(idxs[0]) if idxs[0] else None,
                       int(idxs[1]) if idxs[1] else None]
        if len(idxs) == 3:
            slice_parts.append(int(idxs[2]) if idxs[2] else None)
        else:
            slice_parts.append(None)
        return slice(*slice_parts)
    return int(arg)


def list_of(
    from_str: Callable[[str], T], sep: str = ','
) -> Callable[[str], Tuple[T, ...]]:
    """Return a parser of a comma-separated list of a given type.

    For example, `list_of(float)` can be use to parse `"3.2,4.5,12.8"` as
    `(3.2, 4.5, 12.8)`.  Each element is stripped before parsing, meaning
    `"3.2, 4.5, 12.8"` will also be accepted by the parser.

    Set `sep` to `None` to split on any whitespace (as does `str.split()`).
    """
    def parser(arg: str) -> Tuple[T, ...]:
        return tuple(from_str(v) for v in map(str.strip, arg.split(sep)) if v)
    return parser
