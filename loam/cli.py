"""Definition of CLI manager."""
import argparse
import copy
import pathlib
import warnings
from types import MappingProxyType

from . import error, _internal


BLK = ' \\\n'  # cutting line in scripts


def _names(section, option):
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
        help (str): short description of the sub command.
        sections (tuple of str): configuration sections used by the subcommand.
        defaults (dict): default value of options associated to the subcommand.
    """

    def __init__(self, help_msg, *sections, **defaults):
        self.help = help_msg
        self.sections = sections
        self.defaults = defaults


class CLIManager:
    """CLI manager.

    Args:
        conf_manager_ (:class:`~loam.manager.ConfigurationManager`): the
            configuration manager holding option definitions.
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

    def __init__(self, conf_manager_, common_=None, bare_=None, **subcmds):
        self._conf = conf_manager_
        self._subcmds = {}
        for sub_name, sub_meta in subcmds.items():
            if sub_name.isidentifier():
                self._subcmds[sub_name] = sub_meta
            else:
                raise error.SubcmdError(sub_name)
        self._common = common_ if common_ is not None else Subcmd(None)
        self._bare = bare_
        # dict of dict [command][option] = section
        self._opt_cmds = {}
        # same as above but for bare command only [option] = section
        self._opt_bare = {}
        if self.bare is not None:
            self._cmd_opts_solver(None)
        for cmd_name in self.subcmds:
            self._opt_cmds[cmd_name] = {}
            self._cmd_opts_solver(cmd_name)
        self._parser = self._build_parser()

    @property
    def common(self):
        """Subcmd describing sections common to all subcommands."""
        return self._common

    @property
    def bare(self):
        """Subcmd used when the CLI tool is invoked without subcommand."""
        return self._bare

    @property
    def subcmds(self):
        """Subcommands description.

        It is a dict of :class:`Subcmd`.
        """
        return MappingProxyType(self._subcmds)

    def sections_list(self, cmd=None):
        """List of config sections used by a command.

        Args:
            cmd (str): command name, set to ``None`` or ``''`` for the bare
                command.

        Returns:
            list of str: list of configuration sections used by that command.
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

    def _cmd_opts_solver(self, cmd_name):
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

    def _add_options_to_parser(self, opts_dict, parser):
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

    def _build_parser(self):
        """Build command line argument parser.

        Returns:
            :class:`argparse.ArgumentParser`: the command line argument parser.
            You probably won't need to use it directly. To parse command line
            arguments and update the :class:`ConfigurationManager` instance
            accordingly, use the :meth:`parse_args` method.
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

    def parse_args(self, arglist=None):
        """Parse arguments and update options accordingly.

        Args:
            arglist (list of str): list of arguments to parse. If set to None,
                ``sys.argv[1:]`` is used.

        Returns:
            :class:`Namespace`: the argument namespace returned by the
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

    def _zsh_comp_command(self, zcf, cmd, grouping, add_help=True):
        """Write zsh _arguments compdef for a given command.

        Args:
            zcf (file): zsh compdef file.
            cmd (str): command name, set to None or '' for bare command.
            grouping (bool): group options (zsh>=5.4).
            add_help (bool): add an help option.
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
            if meta.cmd_kwargs.get('action') == 'append':
                grpfmt, optfmt = "+ '{}'", "'*{}[{}]{}'"
                if meta.comprule is None:
                    meta.comprule = ''
            else:
                grpfmt, optfmt = "+ '({})'", "'{}[{}]{}'"
            if meta.cmd_kwargs.get('action') in no_comp \
               or meta.cmd_kwargs.get('nargs') == 0:
                meta.comprule = None
            if meta.comprule is None:
                compstr = ''
            elif meta.comprule == '':
                optfmt = optfmt.split('[')
                optfmt = optfmt[0] + '=[' + optfmt[1]
                compstr = ': :( )'
            else:
                optfmt = optfmt.split('[')
                optfmt = optfmt[0] + '=[' + optfmt[1]
                compstr = ': :{}'.format(meta.comprule)
            if grouping:
                print(grpfmt.format(opt), end=BLK, file=zcf)
            for name in _names(self._conf[sct], opt):
                print(optfmt.format(name, meta.help.replace("'", "'\"'\"'"),
                                    compstr), end=BLK, file=zcf)

    def zsh_complete(self, path, cmd, *cmds, sourceable=False,
                     force_grouping=False):
        """Write zsh compdef script.

        Args:
            path (path-like): desired path of the compdef script.
            cmd (str): command name that should be completed.
            cmds (str): extra command names that should be completed.
            sourceable (bool): if True, the generated file will contain an
                explicit call to ``compdef``, which means it can be sourced
                to activate CLI completion.
            force_grouping (bool): if True, assume zsh supports grouping of
                options. Otherwise, loam will attempt to check whether
                zsh >= 5.4.
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

    def _bash_comp_command(self, cmd, add_help=True):
        """Build a list of all options for a given command.

        Args:
            cmd (str): command name, set to None or '' for bare command.
            add_help (bool): add an help option.

        Returns:
            list of str: list of CLI options strings.
        """
        out = ['-h', '--help'] if add_help else []
        cmd_dict = self._opt_cmds[cmd] if cmd else self._opt_bare
        for opt, sct in cmd_dict.items():
            out.extend(_names(self._conf[sct], opt))
        return out

    def bash_complete(self, path, cmd, *cmds):
        """Write bash complete script.

        Args:
            path (path-like): desired path of the complete script.
            cmd (str): command name that should be completed.
            cmds (str): extra command names that should be completed.
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
