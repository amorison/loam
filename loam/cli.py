"""Definition of CLI manager."""
import argparse
import copy
import pathlib
from types import MappingProxyType

from . import error, internal


BLK = ' \\\n'  # cutting line in scripts


def _names(section, option):
    """List of cli strings for a given option."""
    meta = section.def_[option]
    action = meta.cmd_kwargs.get('action')
    if action is internal.Switch:
        names = ['-{}'.format(option), '+{}'.format(option)]
        if meta.shortname is not None:
            names.append('-{}'.format(meta.shortname))
            names.append('+{}'.format(meta.shortname))
    else:
        names = ['--{}'.format(option)]
        if meta.shortname is not None:
            names.append('-{}'.format(meta.shortname))
    return names


def _add_section_to_parser(section, parser):
    """Add arguments to a parser."""
    store_bool = ('store_true', 'store_false')
    for arg, meta in section.defaults_():
        if not meta.cmd_arg:
            continue
        kwargs = copy.deepcopy(meta.cmd_kwargs)
        action = kwargs.get('action')
        if action is internal.Switch:
            kwargs.update(nargs=0)
        elif meta.default is not None and action not in store_bool:
            kwargs.setdefault('type', type(meta.default))
        kwargs.update(help=meta.help)
        parser.add_argument(*_names(section, arg), **kwargs)
    parser.set_defaults(**{a: section[a]
                           for a, m in section.defaults_() if m.cmd_arg})


def _update_section_from_cmd_args(section, args, exclude=None):
    """Set option values accordingly to cmd line args."""
    if exclude is None:
        exclude = set()
    for opt, meta in section.defaults_():
        if opt in exclude or not meta.cmd_arg:
            continue
        section[opt] = getattr(args, opt, None)


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

    """CLI manager."""

    def __init__(self, conf_manager_, common_=None, bare_=None, **subcmds):
        """Initialization of instances:

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
        self._conf = conf_manager_
        self._subcmds = {}
        for sub_name, sub_meta in subcmds.items():
            if sub_name.isidentifier():
                self._subcmds[sub_name] = sub_meta
            else:
                raise error.SubcmdError(sub_name)
        self._common = common_ if common_ is not None else Subcmd(None)
        self._bare = bare_
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

    def _build_parser(self):
        """Build command line argument parser.

        Returns:
            :class:`argparse.ArgumentParser`: the command line argument parser.
            You probably won't need to use it directly. To parse command line
            arguments and update the :class:`ConfigurationManager` instance
            accordingly, use the :meth:`parse_args` method.
        """
        sub_cmds = self.subcmds
        main_parser = argparse.ArgumentParser(description=self.common.help,
                                              prefix_chars='-+')

        main_parser.set_defaults(**self.common.defaults)
        if self.bare is not None:
            main_parser.set_defaults(**self.bare.defaults)
            for sct in self.common.sections:
                _add_section_to_parser(self._conf[sct], main_parser)
            for sct in self.bare.sections:
                _add_section_to_parser(self._conf[sct], main_parser)

        xparsers = {}
        for sct in self._conf:
            if sct not in sub_cmds:
                xparsers[sct] = argparse.ArgumentParser(add_help=False,
                                                        prefix_chars='-+')
                _add_section_to_parser(self._conf[sct], xparsers[sct])

        subparsers = main_parser.add_subparsers(dest='loam_sub_name')
        for sub_cmd, meta in sub_cmds.items():
            kwargs = {'prefix_chars': '+-', 'help': meta.help}
            parent_parsers = [xparsers[sct]
                              for sct in self.common.sections]
            for sct in meta.sections:
                parent_parsers.append(xparsers[sct])
            kwargs.update(parents=parent_parsers)
            dummy_parser = subparsers.add_parser(sub_cmd, **kwargs)
            if sub_cmd in self._conf:
                _add_section_to_parser(self._conf[sub_cmd], dummy_parser)
            dummy_parser.set_defaults(**meta.defaults)

        return main_parser

    def parse_args(self, arglist=None):
        """Parse arguments and update options accordingly.

        The :meth:`ConfigurationManager.build_parser_` method needs to be
        called prior to this function.

        Args:
            arglist (list of str): list of arguments to parse. If set to None,
                ``sys.argv[1:]`` is used.

        Returns:
            (:class:`Namespace`, list of str): the argument namespace returned
            by the :class:`argparse.ArgumentParser` and the list of
            configuration sections altered by the parsing.
        """
        args = self._parser.parse_args(args=arglist)
        sub_cmd = args.loam_sub_name
        sub_cmds = self.subcmds
        scts = list(self.common.sections)
        if sub_cmd is None:
            if self.bare is not None:
                scts.extend(self.bare.sections)
        else:
            scts.extend(sub_cmds[sub_cmd].sections)
            if sub_cmd in self._conf:
                scts.append(sub_cmd)
        already_consumed = set()
        for sct in scts:
            _update_section_from_cmd_args(self._conf[sct], args)
            already_consumed |= set(o for o, m in self._conf[sct].defaults_()
                                    if m.cmd_arg)
        # set sections implemented by empty subcommand with remaining options
        if sub_cmd is not None and self.bare is not None:
            for sct in self.bare.sections:
                _update_section_from_cmd_args(self._conf[sct], args,
                                              already_consumed)
        return args, scts

    def _zsh_comp_sections(self, zcf, sections, grouping, add_help=True):
        """Write zsh _arguments compdef for a list of sections.

        Args:
            zcf (file): zsh compdef file.
            sections (list of str): list of sections.
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
        for sec in sections:
            for opt, meta in self._conf[sec].defaults_():
                if not meta.cmd_arg:
                    continue
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
                for name in _names(self._conf[sec], opt):
                    print(optfmt.format(name,
                                        meta.help.replace("'", "'\"'\"'"),
                                        compstr),
                          end=BLK, file=zcf)

    def zsh_complete(self, path, cmd, *cmds, sourceable=False):
        """Write zsh compdef script.

        Args:
            path (path-like): desired path of the compdef script.
            cmd (str): command name that should be completed.
            cmds (str): extra command names that should be completed.
            sourceable (bool): if True, the generated file will contain an
                explicit call to ``compdef``, which means it can be sourced
                to activate CLI completion.
        """
        grouping = internal.zsh_version() >= (5, 4)
        path = pathlib.Path(path)
        firstline = ['#compdef', cmd]
        firstline.extend(cmds)
        subcmds = list(self.subcmds.keys())
        with path.open('w') as zcf:
            print(*firstline, end='\n\n', file=zcf)
            # main function
            print('function _{} {{'.format(cmd), file=zcf)
            print('local line', file=zcf)
            print('_arguments -C', end=BLK, file=zcf)
            if subcmds:
                # list of subcommands and their description
                substrs = ["{}\\:'{}'".format(sub, self.subcmds[sub].help)
                           for sub in subcmds]
                print('"1:Commands:(({}))"'.format(' '.join(substrs)),
                      end=BLK, file=zcf)
            sections = []
            if self.bare is not None:
                sections.extend(self.common.sections)
                sections.extend(self.bare.sections)
            self._zsh_comp_sections(zcf, sections, grouping)
            if subcmds:
                print("'*::arg:->args'", file=zcf)
                print('case $line[1] in', file=zcf)
                for sub in subcmds:
                    print('{sub}) _{cmd}_{sub} ;;'.format(sub=sub, cmd=cmd),
                          file=zcf)
                print('esac', file=zcf)
            print('}', file=zcf)
            # all subcommand completion handlers
            for sub in subcmds:
                print('\nfunction _{}_{} {{'.format(cmd, sub), file=zcf)
                print('_arguments', end=BLK, file=zcf)
                sections = []
                sections.extend(self.common.sections)
                sections.extend(self.subcmds[sub].sections)
                if sub in self._conf:
                    sections.append(sub)
                self._zsh_comp_sections(zcf, sections, grouping)
                print('}', file=zcf)
            if sourceable:
                print('\ncompdef _{0} {0}'.format(cmd), *cmds, file=zcf)

    def _bash_comp_sections(self, sections, add_help=True):
        """Build a list of all options from a list of sections.

        Args:
            sections (list of str): list of sections.
            add_help (bool): add an help option.

        Returns:
            list of str: list of CLI options strings.
        """
        out = ['-h', '--help'] if add_help else []
        for sec in sections:
            for opt, meta in self._conf[sec].defaults_():
                if not meta.cmd_arg:
                    continue
                out.extend(_names(self._conf[sec], opt))
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
            print('_{}() {{'.format(cmd), file=bcf)
            print('COMPREPLY=()', file=bcf)
            print(r'local cur=${COMP_WORDS[COMP_CWORD]}', end='\n\n', file=bcf)
            sections = []
            if self.bare is not None:
                sections.extend(self.common.sections)
                sections.extend(self.bare.sections)
            optstr = ' '.join(self._bash_comp_sections(sections))
            print(r'local options="{}"'.format(optstr), end='\n\n', file=bcf)
            if subcmds:
                print('local commands="{}"'.format(' '.join(subcmds)),
                      file=bcf)
                print('declare -A suboptions', file=bcf)
            for sub in subcmds:
                sections = []
                sections.extend(self.common.sections)
                sections.extend(self.subcmds[sub].sections)
                if sub in self._conf:
                    sections.append(sub)
                optstr = ' '.join(self._bash_comp_sections(sections))
                print('suboptions[{}]="{}"'.format(sub, optstr), file=bcf)
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
            print('complete -F _{0} {0}'.format(cmd), *cmds, file=bcf)
