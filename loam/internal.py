"""Internal objects.

You should not use these in your own script.
"""

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
        """Set args attribute with True/False"""
        setattr(namespace, self.dest, bool('-+'.index(option_string[0])))


def zsh_version():
    """Try to guess zsh version, returns (0, 0) on failure."""
    try:
        out = str(subprocess.check_output(shlex.split('zsh --version')))
    except (FileNotFoundError, subprocess.CalledProcessError):
        return (0, 0)
    match = re.search('[0-9]+\.[0-9]+', out)
    return tuple(map(int, match[0].split('.'))) if match else (0, 0)
