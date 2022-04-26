"""Various helper functions and classes."""

from __future__ import annotations
from dataclasses import dataclass
import pathlib
import subprocess
import shlex
import typing

from . import _internal
from .base import Entry, Section, Config

if typing.TYPE_CHECKING:
    from pathlib import Path
    from typing import Optional, Union, Type
    from os import PathLike
    from .cli import CLIManager


def switch_opt(default: bool, shortname: Optional[str],
               doc: str) -> bool:
    """Define a switchable option.

    This creates a boolean option. If you use it in your CLI, it can be
    switched on and off by prepending + or - to its name: +opt / -opt.

    Args:
        default: the default value of the swith option.
        shortname: short name of the option, no shortname will be used if set
            to None.
        doc: short description of the option.
    """
    return Entry(
        val=default, doc=doc, cli_short=shortname,
        cli_kwargs=dict(action=_internal.Switch), cli_zsh_comprule=None
    ).field()


def command_flag(doc: str, shortname: Optional[str] = None) -> bool:
    """Define a command line flag.

    The corresponding option is set to true if it is passed as a command line
    option.  This is similar to :func:`switch_opt`, except the option is not
    available from config files.  There is therefore no need for a mechanism to
    switch it off from the command line.

    Args:
        doc: short description of the option.
        shortname: short name of the option, no shortname will be used if set
            to None.
    """
    return Entry(  # previously, default value was None. Diff in cli?
        val=False, doc=doc, in_file=False, cli_short=shortname,
        cli_kwargs=dict(action="store_true"), cli_zsh_comprule=None
    ).field()


@dataclass
class ConfigSection(Section):
    """A configuration section handling config files."""

    create: bool = command_flag("create global config file")
    update: bool = command_flag("add missing entries to config file")
    edit: bool = command_flag("open config file in a text editor")
    editor: str = Entry(val="vim", doc='text editor').field()


def config_cmd_handler(
        config: Union[Config, Type[Config]],
        config_section: ConfigSection,
        config_file: Path,
) -> None:
    """Implement the behavior of a subcmd using config_conf_section.

    Args:
        config: the :class:`~loam.base.Config` to manage.
        config_section: a :class:`ConfigSection` set as desired.
        config_file: path to the config file.
    """
    if config_section.update:
        conf = config.default_()
        if config_file.exists():
            conf.update_from_file_(config_file)
        conf.to_file_(config_file)
    elif config_section.create or config_section.edit:
        config.default_().to_file_(config_file)
    if config_section.edit:
        subprocess.run(shlex.split('{} {}'.format(config_section.editor,
                                                  config_file)))


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
