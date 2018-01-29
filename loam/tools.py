"""Various helper functions and classes.

They are designed to help you use :class:`~loam.manager.ConfigurationManager`.
"""

from collections import namedtuple, OrderedDict
from subprocess import call
import argparse
import shlex


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


def config_conf_section():
    """Define a configuration section handling config file.

    Returns:
        dict of ConfOpt: it defines the 'create', 'update', 'edit' and 'editor'
        configuration options.
    """
    config_dict = OrderedDict((
        ('create',
            ConfOpt(None, True, None, {'action': 'store_true'},
                    False, 'create new config file')),
        ('update',
            ConfOpt(None, True, None, {'action': 'store_true'},
                    False, 'add missing entries to config file')),
        ('edit',
            ConfOpt(None, True, None, {'action': 'store_true'},
                    False, 'open config file in a text editor')),
        ('editor',
            ConfOpt('vim', False, None, {}, True, 'text editor')),
    ))
    return config_dict


def config_cmd_handler(conf, config='config'):
    """Implement the behavior of a subcmd using config_conf_section

    Args:
        conf (:class:`~loam.manager.ConfigurationManager`): it should contain a
            section created with :func:`config_conf_section` function.
        config (str): name of the configuration section created with
            :func:`config_conf_section` function.
    """
    if conf[config].create or conf[config].update:
        conf.create_config_(conf[config].update)
    if conf[config].edit:
        call(shlex.split('{} {}'.format(conf[config].editor,
                                        conf.config_file_)))
