"""Definition of configuration manager classes.

Note:
    All methods and attributes are postfixed with an underscore to minimize the
    risk of collision with the names of your configuration sections and
    options.
"""
import argparse
import copy
import pathlib
from types import MappingProxyType

import toml

from . import error, tools


BLK = ' \\\n'  # cutting line in scripts


class _SubConfig:

    """Hold options for a single section."""

    def __init__(self, parent, name):
        self._parent = parent
        self._name = name
        for opt, meta in self.defaults_():
            self[opt] = meta.default

    @property
    def def_(self):
        return self._parent.def_[self._name]

    def __getitem__(self, key):
        return getattr(self, key)

    def __setitem__(self, key, value):
        setattr(self, key, value)

    def __delitem__(self, option):
        delattr(self, option)

    def __getattr__(self, option):
        if option in self.def_:
            self[option] = self.def_[option].default
        else:
            raise error.OptionError(option)
        return self[option]

    def __iter__(self):
        return iter(self.def_.keys())

    def __contains__(self, opt):
        return opt in self.def_

    def options_(self):
        """Iterator over configuration option names.

        Yields:
            option names.
        """
        return iter(self)

    def opt_vals_(self):
        """Iterator over option names and option values.

        Yields:
            tuples with option names, and option values.
        """
        for opt in self.options_():
            yield opt, self[opt]

    def defaults_(self):
        """Iterator over option names, and option metadata.

        Yields:
            tuples with option names, and :class:`Conf` instances holding
            option metadata.
        """
        return self.def_.items()

    def update_(self, secdict, conf_arg=True):
        """Update values of configuration section with dict.

        Args:
            conf_dict (dict): dict indexed with option names.
            conf_arg (bool): if True, only options that can be set in a config
            file are updated.
        """
        for option, value in secdict.items():
            if not conf_arg or self.def_[option].conf_arg:
                self[option] = value

    def names_(self, arg):
        """List of cli strings for a given option."""
        meta = self.def_[arg]
        action = meta.cmd_kwargs.get('action')
        if action is tools.Switch:
            names = ['-{}'.format(arg), '+{}'.format(arg)]
            if meta.shortname is not None:
                names.append('-{}'.format(meta.shortname))
                names.append('+{}'.format(meta.shortname))
        else:
            names = ['--{}'.format(arg)]
            if meta.shortname is not None:
                names.append('-{}'.format(meta.shortname))
        return names

    def add_to_parser_(self, parser):
        """Add arguments to a parser."""
        store_bool = ('store_true', 'store_false')
        for arg, meta in self.defaults_():
            if not meta.cmd_arg:
                continue
            kwargs = copy.deepcopy(meta.cmd_kwargs)
            action = kwargs.get('action')
            if action is tools.Switch:
                kwargs.update(nargs=0)
            elif meta.default is not None and action not in store_bool:
                kwargs.setdefault('type', type(meta.default))
            kwargs.update(help=meta.help)
            parser.add_argument(*self.names_(arg), **kwargs)
        parser.set_defaults(**{a: self[a]
                               for a, m in self.defaults_() if m.cmd_arg})

    def update_from_cmd_args_(self, args, exclude=None):
        """Set option values accordingly to cmd line args."""
        if exclude is None:
            exclude = set()
        for opt, meta in self.defaults_():
            if opt in exclude or not meta.cmd_arg:
                continue
            self[opt] = getattr(args, opt, None)


class ConfigurationManager:

    """Configuration manager.

    Configuration options are organized in sections. A configuration option can
    be accessed both with attribute and item access notations, these two lines
    access the same option value::

        conf.some_section.some_option
        conf['some_section']['some_option']

    To reset a configuration option (or an entire section) to its default
    value, simply delete it (with item or attribute notation)::

        del conf['some_section']  # reset all options in 'some_section'
        del conf.some_section.some_option  # reset a particular option

    It will be set to its default value the next time you access it.
    """

    def __init__(self, meta, *config_files, sub_cmds=None):
        """Initialization of instances.

        Args:
            meta (dict): all the metadata describing the config options. It
                should be a dictionary with section names as key. Its values
                should be dictionaries as well, with option names as keys, and
                option metadata as values. Option metadata should be objects
                with the following attributes:

                - default: the default value of the option.
                - cmd_arg (bool): whether the option should be considered as
                  a command line option (CLI parser only).
                - shortname (str): short name of command line argument (CLI
                  parser only).
                - cmd_kwargs (dict): extra kwargs that should be passed on to
                  argparser (CLI parser only).
                - conf_arg (bool): whether the option should be considered as
                  a configuration file option (config file only).
                - help (str): help message describing the option.
            config_files (pathlike): list of path of config files, given in the
                order of reading.
            sub_cmds (dict of :class:`~loam.tools.Subcmd`): the sub commands
                description.
        """
        self._def = MappingProxyType({name: MappingProxyType(sub)
                                      for name, sub in meta.items()})
        self._parser = None
        for sub in self.subs_():
            self[sub] = _SubConfig(self, sub)
        self._nosub_valid = False
        self.sub_cmds_ = sub_cmds
        self.config_files_ = config_files

    @property
    def def_(self):
        """Metadata describing the conf options."""
        return self._def

    @property
    def sub_cmds_(self):
        """Subcommands description.

        It is a dict of :class:`~loam.tools.Subcmd`.
        """
        return self._sub_cmds

    @sub_cmds_.setter
    def sub_cmds_(self, sub_cmds):
        self._sub_cmds = sub_cmds
        self._nosub_valid = sub_cmds is not None and '' in sub_cmds

    @property
    def config_files_(self):
        """Path of config files.

        List of pathlib.Path instances. The config files are in the order of
        reading. This means the most global config file is the first one on
        this list while the most local config file is the last one.
        """
        return self._config_files

    @config_files_.setter
    def config_files_(self, paths):
        self._config_files = [pathlib.Path(path) for path in paths]

    def __getitem__(self, key):
        return getattr(self, key)

    def __setitem__(self, key, value):
        setattr(self, key, value)

    def __delitem__(self, sub):
        delattr(self, sub)

    def __getattr__(self, sub):
        if sub in self.def_:
            self[sub] = _SubConfig(self, sub)
        else:
            raise error.SectionError(sub)
        return self[sub]

    def __iter__(self):
        return iter(self.def_.keys())

    def __contains__(self, sub):
        return sub in self.def_

    def subs_(self):
        """Iterator over configuration subsection names.

        Yields:
            subsection names.
        """
        return iter(self)

    def options_(self):
        """Iterator over subsection and option names.

        This iterator is also implemented at the subsection level. The two
        loops produce the same output::

            for sub, opt in conf.options_():
                print(sub, opt)

            for sub in conf.subs_():
                for opt in conf[sub].options_():
                    print(sub, opt)

        Yields:
            tuples with subsection and options names.
        """
        for sub in self:
            for opt in self.def_[sub]:
                yield sub, opt

    def opt_vals_(self):
        """Iterator over subsection, option names, and option values.

        This iterator is also implemented at the subsection level. The two
        loops produce the same output::

            for sub, opt, val in conf.opt_vals_():
                print(sub, opt, val)

            for sub in conf.subs_():
                for opt, val in conf[sub].opt_vals_():
                    print(sub, opt, val)

        Yields:
            tuples with subsection, option names, and option values.
        """
        for sub, opt in self.options_():
            yield sub, opt, self[sub][opt]

    def defaults_(self):
        """Iterator over subsection, option names, and option metadata.

        This iterator is also implemented at the subsection level. The two
        loops produce the same output::

            for sub, opt, meta in conf.defaults_():
                print(sub, opt, meta.default)

            for sub in conf.subs_():
                for opt, meta in conf[sub].defaults_():
                    print(sub, opt, meta.default)

        Yields:
            tuples with subsection, option names, and :class:`Conf`
            instances holding option metadata.
        """
        for sub, opt in self.options_():
            yield sub, opt, self.def_[sub][opt]

    def reset_(self):
        """Restore default values of all options."""
        for sub, opt, meta in self.defaults_():
            self[sub][opt] = meta.default

    def create_config_(self, index=0, update=False):
        """Create config file.

        Create config file in :attr:`config_files_[index]`.

        Parameters:
            index(int): index of config file.
            update (bool): if set to True and :attr:`config_files_` already
                exists, its content is read and all the options it sets are
                kept in the produced config file.
        """
        if not self.config_files_[index:]:
            return
        path = self.config_files_[index]
        if not path.parent.exists():
            path.parent.mkdir(parents=True)
        conf_dict = {}
        for section in self.subs_():
            conf_opts = [o for o, m in self[section].defaults_() if m.conf_arg]
            if not conf_opts:
                continue
            conf_dict[section] = {}
            for opt in conf_opts:
                conf_dict[section][opt] = (self[section][opt] if update else
                                           self.def_[section][opt].default)
        with path.open('w') as cfile:
            toml.dump(conf_dict, cfile)

    def update_(self, conf_dict, conf_arg=True):
        """Update values of configuration options with dict.

        Args:
            conf_dict (dict): dict of dict indexed with section and option
            names.
            conf_arg (bool): if True, only options that can be set in a config
            file are updated.
        """
        for section, secdict in conf_dict.items():
            self[section].update_(secdict, conf_arg)

    def read_config_(self, cfile):
        """Read a config file and set config values accordingly.

        Returns:
            dict: content of config file.
        """
        if not cfile.exists():
            return {}
        try:
            conf_dict = toml.load(str(cfile))
        except toml.TomlDecodeError:
            return None
        self.update_(conf_dict)
        return conf_dict

    def read_configs_(self):
        """Read config files and set config values accordingly.

        Returns:
            (dict, list, list): respectively content of files, list of
            missing/empty files and list of files for which a parsing error
            arised.
        """
        if not self.config_files_:
            return {}, [], []
        content = {section: {} for section in self}
        empty_files = []
        faulty_files = []
        for cfile in self.config_files_:
            conf_dict = self.read_config_(cfile)
            if conf_dict is None:
                faulty_files.append(cfile)
                continue
            elif not conf_dict:
                empty_files.append(cfile)
                continue
            for section, secdict in conf_dict.items():
                content[section].update(secdict)
        return content, empty_files, faulty_files

    def build_parser_(self):
        """Build command line argument parser.

        :attr:`sub_cmds_` must be set.

        Returns:
            :class:`argparse.ArgumentParser`: the command line argument parser.
            You probably won't need to use it directly. To parse command line
            arguments and update the :class:`ConfigurationManager` instance
            accordingly, use the :meth:`ConfigurationManager.parse_args_`
            method.
        """
        sub_cmds = self.sub_cmds_
        if None not in sub_cmds:
            sub_cmds[None] = tools.Subcmd([], {}, None)
        main_parser = argparse.ArgumentParser(description=sub_cmds[None].help,
                                              prefix_chars='-+')

        main_parser.set_defaults(**sub_cmds[None].defaults)
        if self._nosub_valid:
            main_parser.set_defaults(**sub_cmds[''].defaults)
            for sub in sub_cmds[None].extra_parsers:
                self[sub].add_to_parser_(main_parser)
            for sub in sub_cmds[''].extra_parsers:
                self[sub].add_to_parser_(main_parser)
        else:
            sub_cmds[''] = tools.Subcmd([], {}, None)

        xparsers = {}
        for sub in self:
            if sub not in sub_cmds:
                xparsers[sub] = argparse.ArgumentParser(add_help=False,
                                                        prefix_chars='-+')
                self[sub].add_to_parser_(xparsers[sub])

        subparsers = main_parser.add_subparsers(dest='loam_sub_name')
        for sub_cmd, meta in sub_cmds.items():
            if sub_cmd is None or sub_cmd == '':
                continue
            kwargs = {'prefix_chars': '+-', 'help': meta.help}
            parent_parsers = [xparsers[sub]
                              for sub in sub_cmds[None].extra_parsers]
            for sub in meta.extra_parsers:
                parent_parsers.append(xparsers[sub])
            kwargs.update(parents=parent_parsers)
            dummy_parser = subparsers.add_parser(sub_cmd, **kwargs)
            if sub_cmd in self:
                self[sub_cmd].add_to_parser_(dummy_parser)
            dummy_parser.set_defaults(**meta.defaults)

        self._parser = main_parser
        return main_parser

    def parse_args_(self, arglist=None):
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
        if self._parser is None:
            raise error.ParserNotBuiltError(
                'Please call build_parser before parse_args.')
        args = self._parser.parse_args(args=arglist)
        sub_cmd = args.loam_sub_name
        sub_cmds = self._sub_cmds
        if sub_cmd is None:
            sub_cmd = ''
        subs = sub_cmds[None].extra_parsers + sub_cmds[sub_cmd].extra_parsers
        if sub_cmd in self:
            subs.append(sub_cmd)
        already_consumed = set()
        for sub in subs:
            self[sub].update_from_cmd_args_(args)
            already_consumed |= set(o for o, m in self[sub].defaults_()
                                    if m.cmd_arg)
        # set sections implemented by empty subcommand with remaining options
        if sub_cmd != '':
            for sub in sub_cmds[''].extra_parsers:
                self[sub].update_from_cmd_args_(args, already_consumed)
        return args, subs

    def _zsh_comp_sections(self, zcf, sections, add_help=True):
        """Write zsh _arguments compdef for a list of sections.

        Args:
            zcf (file): zsh compdef file.
            sections (list of str): list of sections.
            add_help (bool): add an help option.
        """
        if add_help:
            print("+ '(help)'", end=BLK, file=zcf)
            print("'--help[show help message]'", end=BLK, file=zcf)
            print("'-h[show help message]'", end=BLK, file=zcf)
        # could deal with duplicate by iterating in reverse and keep set of
        # already defined opts.
        no_comp = ('store_true', 'store_false')
        for sec in sections:
            for opt, meta in self[sec].defaults_():
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
                    optfmt = optfmt[0] + '=-[' + optfmt[1]
                    compstr = ': :( )'
                else:
                    optfmt = optfmt.split('[')
                    optfmt = optfmt[0] + '=-[' + optfmt[1]
                    compstr = ': :{}'.format(meta.comprule)
                print(grpfmt.format(opt), end=BLK, file=zcf)
                for name in self[sec].names_(opt):
                    print(optfmt.format(name,
                                        meta.help.replace("'", "'\"'\"'"),
                                        compstr),
                          end=BLK, file=zcf)

    def zsh_complete_(self, path, cmd, *cmds, sourceable=False):
        """Write zsh compdef script.

        Args:
            path (path-like): desired path of the compdef script.
            cmd (str): command name that should be completed.
            cmds (str): extra command names that should be completed.
            sourceable (bool): if True, the generated file will contain an
                explicit call to ``compdef``, which means it can be sourced
                to activate CLI completion.
        """
        if self._sub_cmds is None:
            raise error.ParserNotBuiltError(
                'Subcommand metadata not available, call buid_parser first.')
        path = pathlib.Path(path)
        firstline = ['#compdef', cmd]
        firstline.extend(cmds)
        mdum = tools.Subcmd([], {}, '')
        subcmds = [sub for sub in self.sub_cmds_ if sub]
        with path.open('w') as zcf:
            print(*firstline, end='\n\n', file=zcf)
            # main function
            print('function _{} {{'.format(cmd), file=zcf)
            print('local line', file=zcf)
            print('_arguments -C', end=BLK, file=zcf)
            if subcmds:
                # list of subcommands and their description
                substrs = ["{}\\:'{}'".format(sub, self.sub_cmds_[sub].help)
                           for sub in subcmds]
                print('"1:Commands:(({}))"'.format(' '.join(substrs)),
                      end=BLK, file=zcf)
            sections = []
            if self._nosub_valid:
                sections.extend(self.sub_cmds_.get(None, mdum).extra_parsers)
                sections.extend(self.sub_cmds_.get('', mdum).extra_parsers)
            self._zsh_comp_sections(zcf, sections)
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
                sections.extend(self.sub_cmds_.get(None, mdum).extra_parsers)
                sections.extend(self.sub_cmds_[sub].extra_parsers)
                if sub in self:
                    sections.append(sub)
                self._zsh_comp_sections(zcf, sections)
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
            for opt, meta in self[sec].defaults_():
                if not meta.cmd_arg:
                    continue
                out.extend(self[sec].names_(opt))
        return out

    def bash_complete_(self, path, cmd, *cmds):
        """Write bash complete script.

        Args:
            path (path-like): desired path of the complete script.
            cmd (str): command name that should be completed.
            cmds (str): extra command names that should be completed.
        """
        if self._sub_cmds is None:
            raise error.ParserNotBuiltError(
                'Subcommand metadata not available, call buid_parser first.')
        path = pathlib.Path(path)
        mdum = tools.Subcmd([], {}, '')
        subcmds = [sub for sub in self.sub_cmds_ if sub]
        with path.open('w') as bcf:
            # main function
            print('_{}() {{'.format(cmd), file=bcf)
            print('COMPREPLY=()', file=bcf)
            print(r'local cur=${COMP_WORDS[COMP_CWORD]}', end='\n\n', file=bcf)
            sections = []
            if self._nosub_valid:
                sections.extend(self.sub_cmds_.get(None, mdum).extra_parsers)
                sections.extend(self.sub_cmds_.get('', mdum).extra_parsers)
            optstr = ' '.join(self._bash_comp_sections(sections))
            print(r'local options="{}"'.format(optstr), end='\n\n', file=bcf)
            if subcmds:
                print('local commands="{}"'.format(' '.join(subcmds)),
                      file=bcf)
                print('declare -A suboptions', file=bcf)
            for sub in subcmds:
                sections = []
                sections.extend(self.sub_cmds_.get(None, mdum).extra_parsers)
                sections.extend(self.sub_cmds_[sub].extra_parsers)
                if sub in self:
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
