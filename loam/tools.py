"""Various helper functions and classes.

They are designed to help you use :class:`~loam.manager.ConfigurationManager`.
"""

from collections import OrderedDict
import pathlib
import subprocess
import shlex

from . import error, internal
from .manager import ConfOpt


def switch_opt(default, shortname, help_msg):
    """Define a switchable ConfOpt.

    This creates a boolean option. If you use it in your CLI, it can be
    switched on and off by prepending + or - to its name: +opt / -opt.

    Args:
        default (bool): the default value of the swith option.
        shortname (str): short name of the option, no shortname will be used if
            it is set to None.
        help_msg (str): short description of the option.

    Returns:
        :class:`~loam.manager.ConfOpt`: a configuration option with the given
        properties.
    """
    return ConfOpt(bool(default), True, shortname,
                   dict(action=internal.Switch), True, help_msg, None)


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
        :class:`~loam.manager.ConfOpt`: the option definition.
    """
    return ConfOpt(None, True, shortname,
                   dict(action='append', metavar='section.option=value'),
                   False, 'set configuration options')


def set_conf_str(conf, optstrs):
    """Set options from a list of section.option=value string.

    Args:
        conf (:class:`~loam.manager.ConfigurationManager`): the conf to update.
        optstrs (list of str): the list of 'section.option=value' formatted
            string.
    """
    falsy = ['0', 'no', 'n', 'off', 'false', 'f']
    bool_actions = ['store_true', 'store_false', internal.Switch]
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
        subprocess.call(shlex.split('{} {}'.format(conf[config].editor,
                                                   conf.config_files_[0])))


def create_complete_files(climan, path, cmd, *cmds, zsh_sourceable=False):
    """Create completion files for bash and zsh.

    Args:
        climan (:class:`~loam.cli.CLIManager`): CLI manager.
        path (path-like): directory in which the config files should be
            created. It is created if it doesn't exist.
        cmd (str): command name that should be completed.
        cmds (str): extra command names that should be completed.
        zsh_sourceable (bool): if True, the generated file will contain an
            explicit call to ``compdef``, which means it can be sourced
            to activate CLI completion.
    """
    path = pathlib.Path(path)
    zsh_dir = path / 'zsh'
    if not zsh_dir.exists():
        zsh_dir.mkdir(parents=True)
    zsh_file = zsh_dir / '_{}.sh'.format(cmd)
    bash_dir = path / 'bash'
    if not bash_dir.exists():
        bash_dir.mkdir(parents=True)
    bash_file = bash_dir / '{}.sh'.format(cmd)
    climan.zsh_complete(zsh_file, cmd, *cmds, sourceable=zsh_sourceable)
    climan.bash_complete(bash_file, cmd, *cmds)
