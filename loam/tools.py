from collections import namedtuple
import argparse


ConfOpt = namedtuple('ConfOpt',
                     ['default', 'cmd_arg', 'shortname', 'cmd_kwargs',
                      'conf_arg', 'help'])


Subcmd = namedtuple('Subcmd', ['extra_parsers', 'defaults', 'help'])


class Switch(argparse.Action):

    """argparse Action to store True/False to a +/-arg"""

    def __call__(self, parser, namespace, values, option_string=None):
        """set args attribute with True/False"""
        setattr(namespace, self.dest, bool('-+'.index(option_string[0])))


def bare_opt(default):
    """Define a ConfOpt with only a default value."""
    return ConfOpt(default, False, None, {}, False, '')


def switch_opt(default, shortname, help_msg):
    """Define a ConfOpt with the Switch action."""
    return ConfOpt(
        bool(default), True, shortname, dict(action=Switch), True, help_msg)
