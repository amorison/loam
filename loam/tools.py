"""Various helper functions and classes.

They are designed to help you use :class:`~loam.manager.ConfigurationManager`.
"""

from collections import namedtuple, OrderedDict
from subprocess import call
import argparse
import shlex
from . import error


Subcmd = namedtuple('Subcmd', ['extra_parsers', 'defaults', 'help'])


class ConfOpt:

    """Metadata of configuration options.

    Attributes:
        default: the default value of the configuration option.
        cmd_arg (bool): whether the option is a command line argument.
        shortname (str): short version of the command line argument.
        cmd_kwargs (dict): keyword arguments fed to
            :meth:`argparse.ArgumentParser.add_argument` during the
            construction of the command line arguments parser.
        conf_arg (bool): whether the option can be set in the config file.
        help (str): short description of the option.
        comprule (str): completion rule for ZSH shell.

    """

    def __init__(self, default, cmd_arg=False, shortname=None, cmd_kwargs=None,
                 conf_arg=False, help_msg='', comprule=''):
        self.default = default
        self.cmd_arg = cmd_arg
        self.shortname = shortname
        self.cmd_kwargs = {} if cmd_kwargs is None else cmd_kwargs
        self.conf_arg = conf_arg
        self.help = help_msg
        self.comprule = comprule


class Switch(argparse.Action):

    """Inherited from argparse.Action, store True/False to a +/-arg.

    The :func:`switch_opt` function allows you to easily create a
    :class:`ConfOpt` using this action.
    """

    def __call__(self, parser, namespace, values, option_string=None):
        """Set args attribute with True/False"""
        setattr(namespace, self.dest, bool('-+'.index(option_string[0])))


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
    return ConfOpt(bool(default), True, shortname, dict(action=Switch), True,
                   help_msg, None)


def config_conf_section():
    """Define a configuration section handling config file.

    Returns:
        dict of ConfOpt: it defines the 'create', 'update', 'edit' and 'editor'
        configuration options.
    """
    config_dict = OrderedDict((
        ('create',
            ConfOpt(None, True, None, {'action': 'store_true'},
                    False, 'create most global config file')),
        ('create_local',
            ConfOpt(None, True, None, {'action': 'store_true'},
                    False, 'create most local config file')),
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


def set_conf_opt(shortname=None):
    """Define a Confopt to set a config option.

    You can feed the value of this option to :func:`set_conf_str`.

    Args:
        shortname (str): shortname for the option if relevant.

    Returns:
        :class:`ConfOpt`: the option definition.
    """
    return ConfOpt(None, True, shortname,
                   dict(action='append', metavar='config.option=value'),
                   False, 'set configuration options')


def set_conf_str(conf, optstrs):
    """Set options from a list of section.option=value string.

    Args:
        conf (:class:`~loam.manager.ConfigurationManager`): the conf to update.
        optstrs (list of str): the list of 'section.option=value' formatted
            string.
    """
    falsy = ['0', 'no', 'off', 'false', 'f']
    bool_actions = ['store_true', 'store_false', Switch]
    for optstr in optstrs:
        opt, val = optstr.split('=', 1)
        sec, opt = opt.split('.', 1)
        if sec not in conf:
            raise error.SectionError(sec)
        if opt not in conf[sec]:
            raise error.OptionError(opt)
        meta = conf[sec].def_[opt]
        if meta.default is None:
            if 'type' in meta.cmd_kwargs:
                cast = meta.cmd_kwargs['type']
            else:
                act = meta.cmd_kwargs.get('action')
                cast = bool if act in bool_actions else str
        else:
            cast = type(meta.default)
        if cast is bool and val.lower() in falsy:
            val = ''
        conf[sec][opt] = cast(val)


def config_cmd_handler(conf, config='config'):
    """Implement the behavior of a subcmd using config_conf_section

    Args:
        conf (:class:`~loam.manager.ConfigurationManager`): it should contain a
            section created with :func:`config_conf_section` function.
        config (str): name of the configuration section created with
            :func:`config_conf_section` function.
    """
    if conf[config].create or conf[config].update:
        conf.create_config_(update=conf[config].update)
    if conf[config].create_local:
        conf.create_config_(index=-1, update=conf[config].update)
    if conf[config].edit:
        if not conf.config_files_[0].is_file():
            conf.create_config_(update=conf[config].update)
        call(shlex.split('{} {}'.format(conf[config].editor,
                                        conf.config_files_[0])))
