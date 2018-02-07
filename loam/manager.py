"""Definition of configuration manager classes.

Note:
    All methods and attributes are postfixed with an underscore to minimize the
    risk of collision with the names of your configuration sections and
    options.
"""
import argparse
import configparser
import copy
import pathlib
from types import MappingProxyType
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

    def read_section_(self, config_parser):
        """Read section of config parser and set options accordingly."""
        missing_opts = []
        for opt, meta_opt in self.defaults_():
            if not meta_opt.conf_arg:
                continue
            if not config_parser.has_option(self._name, opt):
                missing_opts.append(opt)
                continue
            if isinstance(meta_opt.default, bool):
                dflt = config_parser.getboolean(self._name, opt)
            elif isinstance(meta_opt.default, float):
                dflt = config_parser.getfloat(self._name, opt)
            elif isinstance(meta_opt.default, int):
                dflt = config_parser.getint(self._name, opt)
            else:
                dflt = config_parser.get(self._name, opt)
            self[opt] = dflt
        return missing_opts

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

    def __init__(self, meta, sub_cmds=None, config_file=None):
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
            sub_cmds (dict of :class:`~loam.tools.Subcmd`): the sub commands
                description.
            config_file (pathlike): path of config file.
        """
        self._def = MappingProxyType({name: MappingProxyType(sub)
                                      for name, sub in meta.items()})
        self._parser = None
        for sub in self.subs_():
            self[sub] = _SubConfig(self, sub)
        self._nosub_valid = False
        self.sub_cmds_ = sub_cmds
        self.config_file_ = config_file

    @property
    def def_(self):
        """Metadata describing the conf options."""
        return self._def

    @property
    def sub_cmds_(self):
        """Path of config file.

        It is None or a pathlib.Path instance.
        """
        return self._sub_cmds

    @sub_cmds_.setter
    def sub_cmds_(self, sub_cmds):
        self._sub_cmds = sub_cmds
        self._nosub_valid = sub_cmds is not None and '' in sub_cmds

    @property
    def config_file_(self):
        """Path of config file.

        It is None or a pathlib.Path instance.
        """
        return self._config_file

    @config_file_.setter
    def config_file_(self, path):
        if path is not None:
            self._config_file = pathlib.Path(path)
        else:
            self._config_file = None

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

    def create_config_(self, update=False):
        """Create config file.

        Create a config file at path :attr:`config_file_`.

        Parameters:
            update (bool): if set to True and :attr:`config_file_` already
                exists, its content is read and all the options it sets are
                kept in the produced config file.
        """
        if not self.config_file_.parent.exists():
            self.config_file_.parent.mkdir(parents=True)
        config_parser = configparser.ConfigParser()
        for sub_cmd in self.subs_():
            conf_defaults = [(o, m) for o, m in self[sub_cmd].defaults_()
                             if m.conf_arg]
            if conf_defaults:
                config_parser.add_section(sub_cmd)
            for opt, opt_meta in conf_defaults:
                if update:
                    val = str(self[sub_cmd][opt])
                else:
                    val = str(opt_meta.default)
                config_parser.set(sub_cmd, opt, val)
        with self.config_file_.open('w') as out_stream:
            config_parser.write(out_stream)

    def read_config_(self):
        """Read config file and set config values accordingly.

        Returns:
            missing_sections, missing_opts (list): list of section names and
            options names that were not present in the config file.
        """
        if self.config_file_ is None:
            return [], {}
        if not self.config_file_.is_file():
            return None, None
        config_parser = configparser.ConfigParser()
        try:
            config_parser.read(str(self.config_file_))
        except configparser.Error:
            return None, None
        missing_sections = []
        missing_opts = {}
        for sub in self.subs_():
            if not any(m.conf_arg for _, m in self[sub].defaults_()):
                continue
            if not config_parser.has_section(sub):
                missing_sections.append(sub)
                continue
            missing_opts[sub] = self[sub].read_section_(config_parser)
        return missing_sections, missing_opts

    def build_parser_(self):
        """Build command line argument parser.

        :attr:`sub_cmds_` must be set.

        Returns:
            :class:`argparse.ArgumentParser`: the command line argument parser.
            You probably won't need to use it directly. To parse command line
            arguments and update the :class:`ConfigurationManager` instance
            accordingly, use the :meth:`ConfigurationManager.parse_args_` method.
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
        for sec in sections:
            for opt, meta in self[sec].defaults_():
                if not meta.cmd_arg:
                    continue
                print("+ '({})'".format(opt), end=BLK, file=zcf)
                for name in self[sec].names_(opt):
                    print("'{}[{}]'".format(name, meta.help),
                          end=BLK, file=zcf)

    def zsh_complete_(self, path, cmd, *cmds):
        """Write zsh compdef script.

        Args:
            path (path-like): desired path of the compdef script.
            cmd (str): command name that should be completed.
            cmds (str): extra command names that should be completed.
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
                sections.extend(self.sub_cmds_[sub].extra_parsers)
                if sub in self:
                    sections.append(sub)
                self._zsh_comp_sections(zcf, sections)
                print('}', file=zcf)

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
