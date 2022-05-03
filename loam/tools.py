"""Various helper functions and classes."""

from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
import subprocess
import shlex
import typing

from . import _internal
from .base import Entry, Section

if typing.TYPE_CHECKING:
    from typing import Optional, Union, Type
    from os import PathLike
    from .base import ConfigBase


def path_entry(
    path: Union[str, PathLike],
    doc: str,
    in_file: bool = True,
    in_cli: bool = True,
    cli_short: Optional[str] = None,
    cli_zsh_only_dirs: bool = False,
    cli_zsh_comprule: Optional[str] = None
) -> Path:
    """Define a path option.

    This creates a path option. See :class:`loam.base.Entry` for the meaning of
    the arguments. By default, the zsh completion rule completes any file. You
    can switch this to only directories with the `cli_zsh_only_dirs` option, or
    set your own completion rule with `cli_zsh_comprule`.
    """
    if cli_zsh_comprule is None:
        cli_zsh_comprule = "_files"
        if cli_zsh_only_dirs:
            cli_zsh_comprule += " -/"
    return Entry(
        val=Path(path),
        doc=doc,
        # TYPE SAFETY: Path behaves as needed
        from_toml=Path,  # type: ignore
        to_toml=str,
        in_file=in_file,
        in_cli=in_cli,
        cli_short=cli_short,
        cli_zsh_comprule=cli_zsh_comprule,
    ).field()


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
        config: Union[ConfigBase, Type[ConfigBase]],
        config_section: ConfigSection,
        config_file: Path,
) -> None:
    """Implement the behavior of a subcmd using config_conf_section.

    Args:
        config: the :class:`~loam.base.ConfigBase` to manage.
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
