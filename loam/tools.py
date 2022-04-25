"""Various helper functions and classes.

They are designed to help you use :class:`~loam.manager.ConfigurationManager`.
"""

from __future__ import annotations
import pathlib
import subprocess
import shlex
import typing

from . import _internal
from .manager import ConfOpt

if typing.TYPE_CHECKING:
    from typing import Optional, Dict, Union
    from os import PathLike
    from .manager import ConfigurationManager
    from .cli import CLIManager


def switch_opt(default: bool, shortname: Optional[str],
               help_msg: str) -> ConfOpt:
    """Define a switchable ConfOpt.

    This creates a boolean option. If you use it in your CLI, it can be
    switched on and off by prepending + or - to its name: +opt / -opt.

    Args:
        default: the default value of the swith option.
        shortname: short name of the option, no shortname will be used if set
            to None.
        help_msg: short description of the option.

    Returns:
        a :class:`~loam.manager.ConfOpt` with the relevant properties.
    """
    return ConfOpt(bool(default), True, shortname,
                   dict(action=_internal.Switch), True, help_msg, None)


def command_flag(shortname: Optional[str], help_msg: str) -> ConfOpt:
    """Define a command line flag.

    The corresponding option is set to true if it is passed as a command line
    option.  This is similar to :func:`switch_opt`, except the option is not
    available from config files.  There is therefore no need for a mechanism to
    switch it off from the command line.

    Args:
        shortname: short name of the option, no shortname will be used if set
            to None.
        help_msg: short description of the option.

    Returns:
        a :class:`~loam.manager.ConfOpt` with the relevant properties.
    """
    return ConfOpt(None, True, shortname, dict(action='store_true'), False,
                   help_msg, None)


def config_conf_section() -> Dict[str, ConfOpt]:
    """Define a configuration section handling config file.

    Returns:
        definition of the 'create', 'create_local', 'update', 'edit' and
        'editor' configuration options.
    """
    return dict(
        create=command_flag(None, 'create most global config file'),
        create_local=command_flag(None, 'create most local config file'),
        update=command_flag(None, 'add missing entries to config file'),
        edit=command_flag(None, 'open config file in a text editor'),
        editor=ConfOpt('vim', conf_arg=True, help='text editor'),
    )


def config_cmd_handler(conf: ConfigurationManager,
                       config: str = 'config') -> None:
    """Implement the behavior of a subcmd using config_conf_section.

    Args:
        conf: a :class:`~loam.manager.ConfigurationManager` containing a
            section created with :func:`config_conf_section` function.
        config: name of the configuration section created with
            :func:`config_conf_section` function.
    """
    if conf[config].create or conf[config].update:
        conf.create_config_(update=conf[config].update)
    if conf[config].create_local:
        conf.create_config_(index=-1, update=conf[config].update)
    if conf[config].edit:
        if not conf.config_files_[0].is_file():
            conf.create_config_(update=conf[config].update)
        subprocess.run(shlex.split('{} {}'.format(conf[config].editor,
                                                  conf.config_files_[0])))


def create_complete_files(climan: CLIManager, path: Union[str, PathLike],
                          cmd: str, *cmds: str, zsh_sourceable: bool = False,
                          zsh_force_grouping: bool = False) -> None:
    """Create completion files for bash and zsh.

    Args:
        climan: a :class:`~loam.cli.CLIManager`.
        path: directory in which the config files should be created. It is
            created if it doesn't exist.
        cmd: command name that should be completed.
        cmds: extra command names that should be completed.
        zsh_sourceable: if True, the generated file will contain an explicit
            call to ``compdef``, which means it can be sourced to activate CLI
            completion.
        zsh_force_grouping: if True, assume zsh supports grouping of options.
            Otherwise, loam will attempt to check whether zsh >= 5.4.
    """
    path = pathlib.Path(path)
    zsh_dir = path / 'zsh'
    zsh_dir.mkdir(parents=True, exist_ok=True)
    zsh_file = zsh_dir / f"_{cmd}.sh"
    bash_dir = path / 'bash'
    bash_dir.mkdir(parents=True, exist_ok=True)
    bash_file = bash_dir / f"{cmd}.sh"
    climan.zsh_complete(zsh_file, cmd, *cmds, sourceable=zsh_sourceable,
                        force_grouping=zsh_force_grouping)
    climan.bash_complete(bash_file, cmd, *cmds)
