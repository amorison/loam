"""Definition of CLI manager."""
from __future__ import annotations
import argparse
import copy
import pathlib
import typing
import warnings
from types import MappingProxyType

from . import error, _internal

if typing.TYPE_CHECKING:
    from typing import Dict, List, Any, Optional, Mapping, TextIO, Union
    from argparse import ArgumentParser, Namespace
    from os import PathLike
    from .manager import Section, ConfigurationManager


BLK = ' \\\n'  # cutting line in scripts


def _names(section: Section, option: str) -> List[str]:
    """List of cli strings for a given option."""
    meta = section.def_[option]
    action = meta.cmd_kwargs.get('action')
    if action is _internal.Switch:
        names = [f'-{option}', f'+{option}']
        if meta.shortname is not None:
            names.append(f'-{meta.shortname}')
            names.append(f'+{meta.shortname}')
    else:
        names = [f'--{option}']
        if meta.shortname is not None:
            names.append(f'-{meta.shortname}')
    return names


class Subcmd:
    """Metadata of sub commands.

    Attributes:
        help: short description of the sub command.
        sections: configuration sections used by the subcommand.
        defaults: default value of options associated to the subcommand.
    """

    def __init__(self, help_msg: str, *sections: str, **defaults: Any):
        self.help = help_msg
        self.sections = sections
        self.defaults = defaults


class CLIManager:
    """CLI manager.

    Args:
        conf_manager_: the :class:`~loam.manager.ConfigurationManager` holding
            option definitions.
        common_: special subcommand, used to define the general description
            of the CLI tool as well as configuration sections used by every
            subcommand.
        bare_: special subcommand, use it to define the configuration
            sections that should be used when you call your CLI tool
            without any subcommand.
        subcmds: all the subcommands of your CLI tool. The name of each
            *subcommand* is the name of the keyword argument passed on to
            this function.
    """

    def __init__(self, conf_manager_: ConfigurationManager,
                 common_: Optional[Subcmd] = None,
                 bare_: Optional[Subcmd] = None,
                 **subcmds: Subcmd):
        self._conf = conf_manager_
        self._subcmds = {}
        for sub_name, sub_meta in subcmds.items():
            if sub_name.isidentifier():
                self._subcmds[sub_name] = sub_meta
            else:
                raise error.SubcmdError(sub_name)
        self._common = common_ if common_ is not None else Subcmd('')
        self._bare = bare_
        # dict of dict [command][option] = section
        self._opt_cmds: Dict[str, Dict[str, str]] = {}
        # same as above but for bare command only [option] = section
        self._opt_bare: Dict[str, str] = {}
        if self.bare is not None:
            self._cmd_opts_solver(None)
        for cmd_name in self.subcmds:
            self._opt_cmds[cmd_name] = {}
            self._cmd_opts_solver(cmd_name)
        self._parser = self._build_parser()

    @property
    def common(self) -> Subcmd:
        """Subcmd describing sections common to all subcommands."""
        return self._common

    @property
    def bare(self) -> Optional[Subcmd]:
        """Subcmd used when the CLI tool is invoked without subcommand."""
        return self._bare

    @property
    def subcmds(self) -> Mapping[str, Subcmd]:
        """Subcommands description."""
        return MappingProxyType(self._subcmds)

    def sections_list(self, cmd: Optional[str] = None) -> List[str]:
        """List of config sections used by a command.

        Args:
            cmd: command name, set to ``None`` or ``''`` for the bare command.

        Returns:
            list of configuration sections used by that command.
        """
        sections = list(self.common.sections)
        if not cmd:
            if self.bare is not None:
                sections.extend(self.bare.sections)
                return sections
            return []
        sections.extend(self.subcmds[cmd].sections)
        if cmd in self._conf:
            sections.append(cmd)
        return sections

    def _cmd_opts_solver(self, cmd_name: Optional[str]) -> None:
        """Scan options related to one command and enrich _opt_cmds."""
        sections = self.sections_list(cmd_name)
        cmd_dict = self._opt_cmds[cmd_name] if cmd_name else self._opt_bare
        for sct in reversed(sections):
            for opt, opt_meta in self._conf[sct].def_.items():
                if not opt_meta.cmd_arg:
                    continue
                if opt not in cmd_dict:
                    cmd_dict[opt] = sct
                else:
                    warnings.warn(
                        'Command <{0}>: {1}.{2} shadowed by {3}.{2}'.format(
                            cmd_name, sct, opt, cmd_dict[opt]),
                        error.LoamWarning, stacklevel=4)

    def _add_options_to_parser(self, opts_dict: Mapping[str, str],
                               parser: ArgumentParser) -> None:
        """Add options to a parser."""
        store_bool = ('store_true', 'store_false')
        for opt, sct in opts_dict.items():
            meta = self._conf[sct].def_[opt]
            kwargs = copy.deepcopy(meta.cmd_kwargs)
            action = kwargs.get('action')
            if action is _internal.Switch:
                kwargs.update(nargs=0)
            elif meta.default is not None and action not in store_bool:
                kwargs.setdefault('type', type(meta.default))
            kwargs.update(help=meta.help)
            kwargs.setdefault('default', self._conf[sct][opt])
            parser.add_argument(*_names(self._conf[sct], opt), **kwargs)

    def _build_parser(self) -> ArgumentParser:
        """Build command line argument parser.

        Returns:
            the command line argument parser.
        """
        main_parser = argparse.ArgumentParser(description=self.common.help,
                                              prefix_chars='-+')

        self._add_options_to_parser(self._opt_bare, main_parser)
        main_parser.set_defaults(**self.common.defaults)
        if self.bare is not None:
            main_parser.set_defaults(**self.bare.defaults)

        subparsers = main_parser.add_subparsers(dest='loam_sub_name')
        for cmd_name, meta in self.subcmds.items():
            kwargs = {'prefix_chars': '+-', 'help': meta.help}
            dummy_parser = subparsers.add_parser(cmd_name, **kwargs)
            self._add_options_to_parser(self._opt_cmds[cmd_name], dummy_parser)
            dummy_parser.set_defaults(**meta.defaults)

        return main_parser

    def parse_args(self, arglist: Optional[List[str]] = None) -> Namespace:
        """Parse arguments and update options accordingly.

        Args:
            arglist: list of arguments to parse. If set to None,
                ``sys.argv[1:]`` is used.

        Returns:
            the argument namespace returned by the
            :class:`argparse.ArgumentParser`.
        """
        args = self._parser.parse_args(args=arglist)
        sub_cmd = args.loam_sub_name
        if sub_cmd is None:
            for opt, sct in self._opt_bare.items():
                self._conf[sct][opt] = getattr(args, opt, None)
        else:
            for opt, sct in self._opt_cmds[sub_cmd].items():
                self._conf[sct][opt] = getattr(args, opt, None)
        return args

    def _zsh_comp_command(self, zcf: TextIO, cmd: Optional[str],
                          grouping: bool, add_help: bool = True) -> None:
        """Write zsh _arguments compdef for a given command.

        Args:
            zcf: zsh compdef file.
            cmd: command name, set to None or '' for bare command.
            grouping: group options (zsh>=5.4).
            add_help: add an help option.
        """
        if add_help:
            if grouping:
                print("+ '(help)'", end=BLK, file=zcf)
            print("'--help[show help message]'", end=BLK, file=zcf)
            print("'-h[show help message]'", end=BLK, file=zcf)
        # could deal with duplicate by iterating in reverse and keep set of
        # already defined opts.
        no_comp = ('store_true', 'store_false')
        cmd_dict = self._opt_cmds[cmd] if cmd else self._opt_bare
        for opt, sct in cmd_dict.items():
            meta = self._conf[sct].def_[opt]
            comprule = meta.comprule
            if meta.cmd_kwargs.get('action') == 'append':
                grpfmt, optfmt = "+ '{}'", "'*{}[{}]{}'"
                if comprule is None:
                    comprule = ''
            else:
                grpfmt, optfmt = "+ '({})'", "'{}[{}]{}'"
            if meta.cmd_kwargs.get('action') in no_comp \
               or meta.cmd_kwargs.get('nargs') == 0:
                comprule = None
            if comprule is None:
                compstr = ''
            elif comprule == '':
                optfmt = optfmt.replace('[', '=[')
                compstr = ': :( )'
            else:
                optfmt = optfmt.replace('[', '=[')
                compstr = f': :{comprule}'
            if grouping:
                print(grpfmt.format(opt), end=BLK, file=zcf)
            for name in _names(self._conf[sct], opt):
                print(optfmt.format(name, meta.help.replace("'", "'\"'\"'"),
                                    compstr), end=BLK, file=zcf)

    def zsh_complete(self, path: Union[str, PathLike], cmd: str, *cmds: str,
                     sourceable: bool = False,
                     force_grouping: bool = False) -> None:
        """Write zsh compdef script.

        Args:
            path: desired path of the compdef script.
            cmd: command name that should be completed.
            cmds: extra command names that should be completed.
            sourceable: if True, the generated file will contain an explicit
                call to ``compdef``, which means it can be sourced to activate
                CLI completion.
            force_grouping: if True, assume zsh supports grouping of options.
                Otherwise, loam will attempt to check whether zsh >= 5.4.
        """
        grouping = force_grouping or _internal.zsh_version() >= (5, 4)
        path = pathlib.Path(path)
        firstline = ['#compdef', cmd]
        firstline.extend(cmds)
        subcmds = list(self.subcmds.keys())
        with path.open('w') as zcf:
            print(*firstline, end='\n\n', file=zcf)
            # main function
            print(f'function _{cmd} {{', file=zcf)
            print('local line', file=zcf)
            print('_arguments -C', end=BLK, file=zcf)
            if subcmds:
                # list of subcommands and their description
                substrs = [rf"{sub}\:'{self.subcmds[sub].help}'"
                           for sub in subcmds]
                print('"1:Commands:(({}))"'.format(' '.join(substrs)),
                      end=BLK, file=zcf)
            self._zsh_comp_command(zcf, None, grouping)
            if subcmds:
                print("'*::arg:->args'", file=zcf)
                print('case $line[1] in', file=zcf)
                for sub in subcmds:
                    print(f'{sub}) _{cmd}_{sub} ;;', file=zcf)
                print('esac', file=zcf)
            print('}', file=zcf)
            # all subcommand completion handlers
            for sub in subcmds:
                print(f'\nfunction _{cmd}_{sub} {{', file=zcf)
                print('_arguments', end=BLK, file=zcf)
                self._zsh_comp_command(zcf, sub, grouping)
                print('}', file=zcf)
            if sourceable:
                print(f'\ncompdef _{cmd} {cmd}', *cmds, file=zcf)

    def _bash_comp_command(self, cmd: Optional[str],
                           add_help: bool = True) -> List[str]:
        """Build a list of all options for a given command.

        Args:
            cmd: command name, set to None or '' for bare command.
            add_help: add an help option.

        Returns:
            list of CLI options strings.
        """
        out = ['-h', '--help'] if add_help else []
        cmd_dict = self._opt_cmds[cmd] if cmd else self._opt_bare
        for opt, sct in cmd_dict.items():
            out.extend(_names(self._conf[sct], opt))
        return out

    def bash_complete(self, path: Union[str, PathLike], cmd: str,
                      *cmds: str) -> None:
        """Write bash complete script.

        Args:
            path: desired path of the complete script.
            cmd: command name that should be completed.
            cmds: extra command names that should be completed.
        """
        path = pathlib.Path(path)
        subcmds = list(self.subcmds.keys())
        with path.open('w') as bcf:
            # main function
            print(f'_{cmd}() {{', file=bcf)
            print('COMPREPLY=()', file=bcf)
            print(r'local cur=${COMP_WORDS[COMP_CWORD]}', end='\n\n', file=bcf)
            optstr = ' '.join(self._bash_comp_command(None))
            print(f'local options="{optstr}"', end='\n\n', file=bcf)
            if subcmds:
                print('local commands="{}"'.format(' '.join(subcmds)),
                      file=bcf)
                print('declare -A suboptions', file=bcf)
            for sub in subcmds:
                optstr = ' '.join(self._bash_comp_command(sub))
                print(f'suboptions[{sub}]="{optstr}"', file=bcf)
            condstr = 'if'
            for sub in subcmds:
                print(condstr, r'[[ "${COMP_LINE}" == *"', sub, '"* ]] ; then',
                      file=bcf)
                print(r'COMPREPLY=( `compgen -W "${suboptions[', sub,
                      r']}" -- ${cur}` )', sep='', file=bcf)
                condstr = 'elif'
            print(condstr, r'[[ ${cur} == -* ]] ; then', file=bcf)
            print(r'COMPREPLY=( `compgen -W "${options}" -- ${cur}`)',
                  file=bcf)
            if subcmds:
                print(r'else', file=bcf)
                print(r'COMPREPLY=( `compgen -W "${commands}" -- ${cur}`)',
                      file=bcf)
            print('fi', file=bcf)
            print('}', end='\n\n', file=bcf)
            print(f'complete -F _{cmd} {cmd}', *cmds, file=bcf)
