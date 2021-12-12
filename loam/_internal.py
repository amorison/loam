"""Internal helpers."""

from __future__ import annotations
import argparse
import re
import shlex
import subprocess
import typing

if typing.TYPE_CHECKING:
    from typing import Dict, Any, Tuple, Mapping, Optional, Type
    from argparse import ArgumentParser, Namespace
    from .manager import Section


class Switch(argparse.Action):
    """Inherited from argparse.Action, store True/False to a +/-arg.

    The :func:`switch_opt` function allows you to easily create a
    :class:`~loam.tools.ConfOpt` using this action.
    """

    def __call__(self, parser: ArgumentParser, namespace: Namespace,
                 values: Any, option_string: Optional[str] = None) -> None:
        """Set args attribute to True or False."""
        if option_string is None:
            raise ValueError("Switch action is not suitable for "
                             "positional arguments.")
        setattr(namespace, self.dest, bool('-+'.index(option_string[0])))


class SectionContext:
    """Context manager to locally change option values.

    It is reusable but not reentrant.

    Args:
        section (Section): configuration section to be managed.
        options (Mapping): mapping between option names and their values in the
            context.
    """

    def __init__(self, section: Section, options: Mapping[str, Any]):
        self._section = section
        self._options = options
        self._old_values: Dict[str, Any] = {}

    def __enter__(self) -> None:
        self._old_values = {}
        for option_name, new_value in self._options.items():
            self._old_values[option_name] = self._section[option_name]
            self._section[option_name] = new_value

    def __exit__(self, e_type: Optional[Type[BaseException]], *_: Any) -> bool:
        for option_name, old_value in self._old_values.items():
            self._section[option_name] = old_value
        return e_type is None


def zsh_version() -> Tuple[int, ...]:
    """Try to guess zsh version, return (0, 0) on failure."""
    try:
        out = subprocess.run(shlex.split('zsh --version'), check=True,
                             stdout=subprocess.PIPE).stdout
    except (FileNotFoundError, subprocess.CalledProcessError):
        return (0, 0)
    match = re.search(br'[0-9]+\.[0-9]+', out)
    return tuple(map(int, match.group(0).split(b'.'))) if match else (0, 0)
