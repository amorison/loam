"""Internal helpers."""

import argparse
import re
import shlex
import subprocess


class Switch(argparse.Action):
    """Inherited from argparse.Action, store True/False to a +/-arg.

    The :func:`switch_opt` function allows you to easily create a
    :class:`~loam.tools.ConfOpt` using this action.
    """

    def __call__(self, parser, namespace, values, option_string=None):
        """Set args attribute to True or False."""
        setattr(namespace, self.dest, bool('-+'.index(option_string[0])))


class SectionContext:
    """Context manager to locally change option values.

    It is reusable but not reentrant.

    Args:
        section (Section): configuration section to be managed.
        options (Mapping): mapping between option names and their values in the
            context.
    """

    def __init__(self, section, options):
        self._section = section
        self._options = options
        self._old_values = {}

    def __enter__(self):
        self._old_values = {}
        for option_name, new_value in self._options.items():
            self._old_values[option_name] = self._section[option_name]
            self._section[option_name] = new_value

    def __exit__(self, e_type, *_):
        for option_name, old_value in self._old_values.items():
            self._section[option_name] = old_value
        return e_type is None


def zsh_version():
    """Try to guess zsh version, return (0, 0) on failure."""
    try:
        out = subprocess.run(shlex.split('zsh --version'), check=True,
                             stdout=subprocess.PIPE).stdout
    except (FileNotFoundError, subprocess.CalledProcessError):
        return (0, 0)
    match = re.search(br'[0-9]+\.[0-9]+', out)
    return tuple(map(int, match.group(0).split(b'.'))) if match else (0, 0)