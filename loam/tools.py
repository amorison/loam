"""Various helper functions and classes."""

from collections import namedtuple
import argparse


ConfOpt = namedtuple('ConfOpt',
                     ['default', 'cmd_arg', 'shortname', 'cmd_kwargs',
                      'conf_arg', 'help'])


Subcmd = namedtuple('Subcmd', ['extra_parsers', 'defaults', 'help'])


class Switch(argparse.Action):

    """Inherited from argparse.Action, store True/False to a +/-arg.

    The :func:`switch_opt` function allows you to easily create a
    :class:`ConfOpt` using this action.
    """

    def __call__(self, parser, namespace, values, option_string=None):
        """Set args attribute with True/False"""
        setattr(namespace, self.dest, bool('-+'.index(option_string[0])))


def bare_opt(default):
    """Define a ConfOpt with only a default value.

    Args:
        default: the default value of the configuration option.

    Returns:
        :class:`ConfOpt`: a configuration option with the default value.
    """
    return ConfOpt(default, False, None, {}, False, '')


def switch_opt(default, shortname, help_msg):
    """Define a ConfOpt with the Switch action.

    Args:
        default (bool): the default value of the swith option.
        shortname (str): short name of the option, no shortname will be used if
            it is set to None.
        help_msg (str): short description of the option.

    Returns:
        :class:`ConfOpt`: a configuration option with the given properties.
    """
    return ConfOpt(
        bool(default), True, shortname, dict(action=Switch), True, help_msg)
