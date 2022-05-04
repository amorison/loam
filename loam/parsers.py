"""Parsers for your CLI arguments.

These functions can be used as `from_toml` in :attr:`~loam.base.Entry`.
"""

from __future__ import annotations
from typing import Union


def strict_slice_parser(arg: object) -> slice:
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


def slice_parser(arg: object) -> slice:
    """Parse a string into a slice.

    Note that this treats a single integer as a slice from 0 to that
    value.  To error out on a single integer, use :func:`strict_slice_parser`.
    To parse it as an integer, use :func:`slice_or_int_parser`.
    """
    soi = slice_or_int_parser(arg)
    if isinstance(soi, int):
        return slice(soi)
    return soi


def slice_or_int_parser(arg: object) -> Union[slice, int]:
    """Parse a string into a slice.

    Note that this treats a single integer as an integer value.  To error out
    on a single integer, use :func:`strict_slice_parser`.  To parse it as a
    slice, use :func:`slice_parser`.
    """
    if isinstance(arg, int):
        return arg
    if isinstance(arg, slice):
        return arg
    if not isinstance(arg, str):
        raise TypeError("arg should be an int, slice, or str")
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
