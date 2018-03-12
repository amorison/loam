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

from . import error, internal


BLK = ' \\\n'  # cutting line in scripts


class ConfOpt:

    """Metadata of configuration options.

    Attributes:
        default: the default value of the configuration option.
        cmd_arg (bool): whether the option is a command line argument.
        shortname (str): short version of the command line argument.
        cmd_kwargs (dict): keyword arguments fed to
            :meth:`argparse.ArgumentParser.add_argument` during the
            construction of the command line arguments parser.
        conf_arg (bool): whether the option can be set in the config file.
        help (str): short description of the option.
        comprule (str): completion rule for ZSH shell.

    """

    def __init__(self, default, cmd_arg=False, shortname=None, cmd_kwargs=None,
                 conf_arg=False, help_msg='', comprule=''):
        self.default = default
        self.cmd_arg = cmd_arg
        self.shortname = shortname
        self.cmd_kwargs = {} if cmd_kwargs is None else cmd_kwargs
        self.conf_arg = conf_arg
        self.help = help_msg
        self.comprule = comprule


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


class Section:

    """Hold options for a single section."""

    def __init__(self, **options):
        """Initialization of instances.

        Args:
            options (:class:`ConfOpt`): option metadata. The name of each
                *option* is the name of the keyword argument passed on to this
                function. Option names should be valid identifiers, otherwise
                an :class:`~loam.error.OptionError` is raised.
        """
        self._def = {}
        for opt_name, opt_meta in options.items():
            if opt_name.isidentifier():
                self._def[opt_name] = opt_meta
                self[opt_name] = opt_meta.default
            else:
                raise error.OptionError(opt_name)

    @property
    def def_(self):
        return MappingProxyType(self._def)

    def __getitem__(self, opt):
        return getattr(self, opt)

    def __setitem__(self, opt, value):
        setattr(self, opt, value)

    def __delitem__(self, opt):
        delattr(self, opt)

    def __delattr__(self, opt):
        if not opt in self:
            raise error.OptionError(opt)
        self[opt] = self.def_[opt].default

    def __getattr__(self, opt):
        raise error.OptionError(opt)

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

    def update_(self, sct_dict, conf_arg=True):
        """Update values of configuration section with dict.

        Args:
            sct_dict (dict): dict indexed with option names. Undefined
                options are discarded.
            conf_arg (bool): if True, only options that can be set in a config
                file are updated.
        """
        for opt, val in sct_dict.items():
            if opt not in self.def_:
                continue
            if not conf_arg or self.def_[opt].conf_arg:
                self[opt] = val

    def reset_(self):
        """Restore default values of options in this section."""
        for opt, meta in self.defaults_():
            self[opt] = meta.default

    def names_(self, arg):
        """List of cli strings for a given option."""
        meta = self.def_[arg]
        action = meta.cmd_kwargs.get('action')
        if action is internal.Switch:
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
            if action is internal.Switch:
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

    def __init__(self, **sections):
        """Initialization of instances.

        Args:
            sections (:class:`~loam.manager.Section`): section metadata. The
                name of each *section* is the name of the keyword argument
                passed on to this function. Section names should be valid
                identifiers, otherwise a :class:`~loam.error.SectionError` is
                raised.
        """
        self._sections = []
        for sct_name, sct_meta in sections.items():
            if sct_name.isidentifier():
                setattr(self, sct_name, Section(**sct_meta.def_))
                self._sections.append(sct_name)
            else:
                raise error.SectionError(sct_name)
        self._parser = None
        self._nosub_valid = False
        self._subcmds = {}
        self._config_files = ()

    @classmethod
    def from_dict_(cls, conf_dict):
        """Use a dictionary to create a :class:`ConfigurationManager`.

        Args:
            conf_dict (dict of dict of :class:`ConfOpt`): the first level of
                keys should be the section names. The second level should be
                the option names. The values are the options metadata.

        Returns:
            :class:`ConfigurationManager`: a configuration manager with the
            requested sections and options.
        """
        return cls(**{name: Section(**opts)
                      for name, opts in conf_dict.items()})

    @property
    def subcmds_(self):
        """Subcommands description.

        It is a dict of :class:`Subcmd`.
        """
        return self._subcmds

    def set_subcmds_(self, common_=None, bare_=None, **subcmds):
        """Define subcommands of your CLI tool.

        All arguments to this function should be :class:`Subcmd` instances.

        Args:
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
        self._subcmds = {}
        for sub_name, sub_meta in subcmds.items():
            if sub_name.isidentifier():
                self._subcmds[sub_name] = sub_meta
            else:
                raise error.SubcmdError(sub_name)
        if common_ is not None:
            self._subcmds[None] = common_
        if bare_ is not None:
            self._subcmds[''] = bare_
            self._nosub_valid = True
        else:
            self._nosub_valid = False

    @property
    def config_files_(self):
        """Path of config files.

        Tuple of pathlib.Path instances. The config files are in the order of
        reading. This means the most global config file is the first one on
        this list while the most local config file is the last one.
        """
        return self._config_files

    def set_config_files_(self, *config_files):
        """Set the list of config files.

        Args:
            config_files (pathlike): path of config files, given in the order
                of reading.
        """
        self._config_files = tuple(pathlib.Path(path) for path in config_files)

    def __getitem__(self, sct):
        return getattr(self, sct)

    def __delitem__(self, sct):
        delattr(self, sct)

    def __delattr__(self, sct):
        self[sct].reset_()

    def __getattr__(self, sct):
        raise error.SectionError(sct)

    def __iter__(self):
        return iter(self._sections)

    def __contains__(self, sct):
        return sct in self._sections

    def sections_(self):
        """Iterator over configuration section names.

        Yields:
            section names.
        """
        return iter(self)

    def options_(self):
        """Iterator over section and option names.

        This iterator is also implemented at the section level. The two loops
        produce the same output::

            for sct, opt in conf.options_():
                print(sct, opt)

            for sct in conf.sections_():
                for opt in conf[sct].options_():
                    print(sct, opt)

        Yields:
            tuples with subsection and options names.
        """
        for sct in self:
            for opt in self[sct]:
                yield sct, opt

    def opt_vals_(self):
        """Iterator over sections, option names, and option values.

        This iterator is also implemented at the section level. The two loops
        produce the same output::

            for sct, opt, val in conf.opt_vals_():
                print(sct, opt, val)

            for sct in conf.sections_():
                for opt, val in conf[sct].opt_vals_():
                    print(sct, opt, val)

        Yields:
            tuples with sections, option names, and option values.
        """
        for sct, opt in self.options_():
            yield sct, opt, self[sct][opt]

    def defaults_(self):
        """Iterator over sections, option names, and option metadata.

        This iterator is also implemented at the section level. The two loops
        produce the same output::

            for sct, opt, meta in conf.defaults_():
                print(sct, opt, meta.default)

            for sct in conf.sections_():
                for opt, meta in conf[sct].defaults_():
                    print(sct, opt, meta.default)

        Yields:
            tuples with sections, option names, and :class:`Conf` instances
            holding option metadata.
        """
        for sct, opt in self.options_():
            yield sct, opt, self[sct].def_[opt]

    def reset_(self):
        """Restore default values of all options."""
        for sct, opt, meta in self.defaults_():
            self[sct][opt] = meta.default

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
        for section in self.sections_():
            conf_opts = [o for o, m in self[section].defaults_() if m.conf_arg]
            if not conf_opts:
                continue
            conf_dict[section] = {}
            for opt in conf_opts:
                conf_dict[section][opt] = (self[section][opt] if update else
                                           self[section].def_[opt].default)
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

        :attr:`subcmds_` must be set.

        Returns:
            :class:`argparse.ArgumentParser`: the command line argument parser.
            You probably won't need to use it directly. To parse command line
            arguments and update the :class:`ConfigurationManager` instance
            accordingly, use the :meth:`ConfigurationManager.parse_args_`
            method.
        """
        sub_cmds = self.subcmds_
        if None not in sub_cmds:
            sub_cmds[None] = Subcmd(None)
        main_parser = argparse.ArgumentParser(description=sub_cmds[None].help,
                                              prefix_chars='-+')

        main_parser.set_defaults(**sub_cmds[None].defaults)
        if self._nosub_valid:
            main_parser.set_defaults(**sub_cmds[''].defaults)
            for sct in sub_cmds[None].sections:
                self[sct].add_to_parser_(main_parser)
            for sct in sub_cmds[''].sections:
                self[sct].add_to_parser_(main_parser)
        else:
            sub_cmds[''] = Subcmd(None)

        xparsers = {}
        for sct in self:
            if sct not in sub_cmds:
                xparsers[sct] = argparse.ArgumentParser(add_help=False,
                                                        prefix_chars='-+')
                self[sct].add_to_parser_(xparsers[sct])

        subparsers = main_parser.add_subparsers(dest='loam_sub_name')
        for sub_cmd, meta in sub_cmds.items():
            if sub_cmd is None or sub_cmd == '':
                continue
            kwargs = {'prefix_chars': '+-', 'help': meta.help}
            parent_parsers = [xparsers[sct]
                              for sct in sub_cmds[None].sections]
            for sct in meta.sections:
                parent_parsers.append(xparsers[sct])
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
        sub_cmds = self._subcmds
        if sub_cmd is None:
            sub_cmd = ''
        scts = list(sub_cmds[None].sections
                    + sub_cmds[sub_cmd].sections)
        if sub_cmd in self:
            scts.append(sub_cmd)
        already_consumed = set()
        for sct in scts:
            self[sct].update_from_cmd_args_(args)
            already_consumed |= set(o for o, m in self[sct].defaults_()
                                    if m.cmd_arg)
        # set sections implemented by empty subcommand with remaining options
        if sub_cmd != '':
            for sct in sub_cmds[''].sections:
                self[sct].update_from_cmd_args_(args, already_consumed)
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
                if grouping:
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
        if self._subcmds is None:
            raise error.ParserNotBuiltError(
                'Subcommand metadata not available, call buid_parser first.')
        grouping = internal.zsh_version() >= (5, 4)
        path = pathlib.Path(path)
        firstline = ['#compdef', cmd]
        firstline.extend(cmds)
        mdum = Subcmd('')
        subcmds = [sub for sub in self.subcmds_ if sub]
        with path.open('w') as zcf:
            print(*firstline, end='\n\n', file=zcf)
            # main function
            print('function _{} {{'.format(cmd), file=zcf)
            print('local line', file=zcf)
            print('_arguments -C', end=BLK, file=zcf)
            if subcmds:
                # list of subcommands and their description
                substrs = ["{}\\:'{}'".format(sub, self.subcmds_[sub].help)
                           for sub in subcmds]
                print('"1:Commands:(({}))"'.format(' '.join(substrs)),
                      end=BLK, file=zcf)
            sections = []
            if self._nosub_valid:
                sections.extend(self.subcmds_.get(None, mdum).sections)
                sections.extend(self.subcmds_.get('', mdum).sections)
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
                sections.extend(self.subcmds_.get(None, mdum).sections)
                sections.extend(self.subcmds_[sub].sections)
                if sub in self:
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
        if self._subcmds is None:
            raise error.ParserNotBuiltError(
                'Subcommand metadata not available, call buid_parser first.')
        path = pathlib.Path(path)
        mdum = Subcmd('')
        subcmds = [sub for sub in self.subcmds_ if sub]
        with path.open('w') as bcf:
            # main function
            print('_{}() {{'.format(cmd), file=bcf)
            print('COMPREPLY=()', file=bcf)
            print(r'local cur=${COMP_WORDS[COMP_CWORD]}', end='\n\n', file=bcf)
            sections = []
            if self._nosub_valid:
                sections.extend(self.subcmds_.get(None, mdum).sections)
                sections.extend(self.subcmds_.get('', mdum).sections)
            optstr = ' '.join(self._bash_comp_sections(sections))
            print(r'local options="{}"'.format(optstr), end='\n\n', file=bcf)
            if subcmds:
                print('local commands="{}"'.format(' '.join(subcmds)),
                      file=bcf)
                print('declare -A suboptions', file=bcf)
            for sub in subcmds:
                sections = []
                sections.extend(self.subcmds_.get(None, mdum).sections)
                sections.extend(self.subcmds_[sub].sections)
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
