"""Definition of configuration manager classes.

Note:
    All methods and attributes are postfixed with an underscore to minimize the
    risk of collision with the names of your configuration sections and
    options.
"""
import pathlib
from types import MappingProxyType

import toml

from . import error


def _is_valid(name):
    """Check if a section or option name is valid."""
    return name.isidentifier() and name != 'loam_sub_name'


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
            if _is_valid(opt_name):
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
            if _is_valid(sct_name):
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
