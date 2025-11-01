"""Various helper functions and classes."""

from __future__ import annotations

import typing
from pathlib import Path

from . import _internal
from .base import Entry

if typing.TYPE_CHECKING:
    from os import PathLike


def path_entry(
    path: str | PathLike,
    doc: str,
    in_file: bool = True,
    in_cli: bool = True,
    cli_short: str | None = None,
    cli_zsh_only_dirs: bool = False,
    cli_zsh_comprule: str | None = None,
) -> Path:
    """Define a path option.

    This creates a path option. See [`Entry`][loam.base.Entry] for the meaning of
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


def switch_opt(default: bool, shortname: str | None, doc: str) -> bool:
    """Define a switchable option.

    This creates a boolean option. If you use it in your CLI, it can be
    switched on and off by prepending `+` or `-` to its name: `+opt` / `-opt`.

    Args:
        default: the default value of the swith option.
        shortname: short name of the option, no shortname will be used if set
            to `None`.
        doc: short description of the option.
    """
    return Entry(
        val=default,
        doc=doc,
        cli_short=shortname,
        cli_kwargs=dict(action=_internal.Switch),
        cli_zsh_comprule=None,
    ).field()


def command_flag(doc: str, shortname: str | None = None) -> bool:
    """Define a command line flag.

    The corresponding option is set to `True` if it is passed as a command line
    option. This is similar to [`switch_opt`][loam.tools.switch_opt], except the
    option is not available from config files. There is therefore no need for a
    mechanism to switch it off from the command line.

    Args:
        doc: short description of the option.
        shortname: short name of the option, no shortname will be used if set
            to None.
    """
    return Entry(  # previously, default value was None. Diff in cli?
        val=False,
        doc=doc,
        in_file=False,
        cli_short=shortname,
        cli_kwargs=dict(action="store_true"),
        cli_zsh_comprule=None,
    ).field()
