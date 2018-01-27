"""Definition of configuration manager classes."""
from collections import namedtuple
import configparser
import pathlib
from .error import SectionError, OptionError


ConfOpt = namedtuple('ConfOpt',
                     ['default', 'cmd_arg', 'shortname', 'cmd_kwargs',
                      'conf_arg', 'help'])

class _SubConfig:

    """Hold options for a single section."""

    def __init__(self, parent, name, defaults):
        self._parent = parent
        self._name = name
        self._def = defaults
        for opt, meta in self.defaults():
            self[opt] = meta.default

    def __getitem__(self, key):
        return getattr(self, key)

    def __setitem__(self, key, value):
        setattr(self, key, value)

    def __delitem__(self, option):
        delattr(self, option)

    def __getattr__(self, option):
        if option in self._def:
            self[option] = self._def[option].default
        else:
            raise OptionError(option)
        return self[option]

    def __iter__(self):
        return iter(self._def.keys())

    def options(self):
        """Iterator over configuration option names.

        Yields:
            option names.
        """
        return iter(self)

    def opt_vals(self):
        """Iterator over option names and option values.

        Yields:
            tuples with option names, and option values.
        """
        for opt in self.options():
            yield opt, self[opt]

    def defaults(self):
        """Iterator over option names, and option metadata.

        Yields:
            tuples with option names, and :class:`Conf` instances holding
            option metadata.
        """
        return self._def.items()

    def read_section(self, config_parser):
        """Read section of config parser and set options accordingly."""
        missing_opts = []
        for opt, meta_opt in self.defaults():
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

    def __init__(self, meta, config_file=None):
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
            config_file (pathlike): path of config file.
        """
        self._def = meta
        for sub in self.subs():
            self[sub] = _SubConfig(self, sub, self._def[sub])
        self.config_file = config_file

    @property
    def config_file(self):
        """Path of config file.

        It is None or a pathlib.Path instance.
        """
        return self._config_file

    @config_file.setter
    def config_file(self, path):
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
        if sub in self._def:
            self[sub] = _SubConfig(self, sub, self._def[sub])
        else:
            raise SectionError(sub)
        return self[sub]

    def __iter__(self):
        return iter(self._def.keys())

    def subs(self):
        """Iterator over configuration subsection names.

        Yields:
            subsection names.
        """
        return iter(self)

    def options(self):
        """Iterator over subsection and option names.

        This iterator is also implemented at the subsection level. The two
        loops produce the same output::

            for sub, opt in conf.options():
                print(sub, opt)

            for sub in conf.subs():
                for opt in conf[sub].options():
                    print(sub, opt)

        Yields:
            tuples with subsection and options names.
        """
        for sub in self:
            for opt in self._def[sub]:
                yield sub, opt

    def opt_vals(self):
        """Iterator over subsection, option names, and option values.

        This iterator is also implemented at the subsection level. The two
        loops produce the same output::

            for sub, opt, val in conf.opt_vals():
                print(sub, opt, val)

            for sub in conf.subs():
                for opt, val in conf[sub].opt_vals():
                    print(sub, opt, val)

        Yields:
            tuples with subsection, option names, and option values.
        """
        for sub, opt in self.options():
            yield sub, opt, self[sub][opt]

    def defaults(self):
        """Iterator over subsection, option names, and option metadata.

        This iterator is also implemented at the subsection level. The two
        loops produce the same output::

            for sub, opt, meta in conf.defaults():
                print(sub, opt, meta.default)

            for sub in conf.subs():
                for opt, meta in conf[sub].defaults():
                    print(sub, opt, meta.default)

        Yields:
            tuples with subsection, option names, and :class:`Conf`
            instances holding option metadata.
        """
        for sub, opt in self.options():
            yield sub, opt, self._def[sub][opt]

    def reset(self):
        """Restore default values of all options."""
        for sub, opt, meta in self.defaults():
            self[sub][opt] = meta.default

    def create_config(self, update=False):
        """Create config file.

        Create a config file at path :attr:`config_file`.

        Parameters:
            update (bool): if set to True and :attr:`config_file` already
                exists, its content is read and all the options it sets are
                kept in the produced config file.
        """
        if not self.config_file.parent.exists():
            self.config_file.parent.mkdir(parents=True)
        config_parser = configparser.ConfigParser()
        for sub_cmd in self.subs():
            config_parser.add_section(sub_cmd)
            for opt, opt_meta in self[sub_cmd].defaults():
                if opt_meta.conf_arg:
                    if update:
                        val = str(self[sub_cmd][opt])
                    else:
                        val = str(opt_meta.default)
                    config_parser.set(sub_cmd, opt, val)
        with self.config_file.open('w') as out_stream:
            config_parser.write(out_stream)

    def read_config(self):
        """Read config file and set config values accordingly.

        Returns:
            missing_sections, missing_opts (list): list of section names and
            options names that were not present in the config file.
        """
        if not self.config_file.is_file():
            return None, None
        config_parser = configparser.ConfigParser()
        try:
            config_parser.read(str(self.config_file))
        except configparser.Error:
            return None, None
        missing_sections = []
        missing_opts = {}
        for sub in self.subs():
            if not config_parser.has_section(sub):
                missing_sections.append(sub)
                continue
            missing_opts[sub] = self[sub].read_section(config_parser)
        return missing_sections, missing_opts
