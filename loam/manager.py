"""Definition of configuration manager classes.

Note:
    All methods and attributes are postfixed with an underscore to minimize the
    risk of collision with the names of your configuration sections and
    options.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from pathlib import Path
from types import MappingProxyType
import typing

import toml

from . import error, _internal

if typing.TYPE_CHECKING:
    from typing import (Dict, List, Any, Union, Tuple, Mapping, Optional,
                        Iterator, Iterable, ContextManager)
    from os import PathLike


def _is_valid(name: str) -> bool:
    """Check if a section or option name is valid."""
    return name.isidentifier() and name != 'loam_sub_name'


@dataclass(frozen=True)
class ConfOpt:
    """Metadata of configuration options.

    Attributes:
        default: the default value of the configuration option.
        cmd_arg: whether the option is a command line argument.
        shortname: short version of the command line argument.
        cmd_kwargs: keyword arguments fed to
            :meth:`argparse.ArgumentParser.add_argument` during the
            construction of the command line arguments parser.
        conf_arg: whether the option can be set in the config file.
        help: short description of the option.
        comprule: completion rule for ZSH shell.
    """

    default: Any
    cmd_arg: bool = False
    shortname: Optional[str] = None
    cmd_kwargs: Dict[str, Any] = field(default_factory=dict)
    conf_arg: bool = False
    help: str = ''
    comprule: Optional[str] = ''


class Section:
    """Hold options for a single section.

    Args:
        options: option metadata. The name of each *option* is the name of the
            keyword argument passed on to this function. Option names should be
            valid identifiers, otherwise an :class:`~loam.error.OptionError` is
            raised.
    """

    def __init__(self, **options: ConfOpt):
        self._def = {}
        for opt_name, opt_meta in options.items():
            if _is_valid(opt_name):
                self._def[opt_name] = opt_meta
                self[opt_name] = opt_meta.default
            else:
                raise error.OptionError(opt_name)

    @property
    def def_(self) -> Mapping[str, Any]:
        """Return mapping of default values of options."""
        return MappingProxyType(self._def)

    def __getitem__(self, opt: str) -> Any:
        return getattr(self, opt)

    def __setitem__(self, opt: str, value: Any) -> None:
        setattr(self, opt, value)

    def __delitem__(self, opt: str) -> None:
        delattr(self, opt)

    def __delattr__(self, opt: str) -> None:
        if opt not in self:
            raise error.OptionError(opt)
        self[opt] = self.def_[opt].default

    def __getattr__(self, opt: str) -> None:
        raise error.OptionError(opt)

    def __iter__(self) -> Iterator[str]:
        return iter(self.def_.keys())

    def __contains__(self, opt: str) -> bool:
        return opt in self.def_

    def options_(self) -> Iterator[str]:
        """Iterate over configuration option names."""
        return iter(self)

    def opt_vals_(self) -> Iterator[Tuple[str, Any]]:
        """Iterate over option names and option values."""
        for opt in self.options_():
            yield opt, self[opt]

    def defaults_(self) -> Iterable[Tuple[str, ConfOpt]]:
        """Iterate over option names, and option metadata."""
        return self.def_.items()

    def update_(self, sct_dict: Mapping[str, Any],
                conf_arg: bool = True) -> None:
        """Update values of configuration section with dict.

        Args:
            sct_dict: mapping of option names to their new values. Unknown
                options are discarded.
            conf_arg: if True, only options that can be set in a config file
                are updated.
        """
        for opt, val in sct_dict.items():
            if opt not in self.def_:
                continue
            if not conf_arg or self.def_[opt].conf_arg:
                self[opt] = val

    def reset_(self) -> None:
        """Restore default values of options in this section."""
        for opt, meta in self.defaults_():
            self[opt] = meta.default

    def context_(self, **options: Any) -> ContextManager[None]:
        """Enter a context to locally change option values.

        This context is reusable but not reentrant.
        """
        return _internal.SectionContext(self, options)


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

    Args:
        sections: section metadata. The name of each *section* is the name of
            the keyword argument passed on to this function. Section names
            should be valid identifiers, otherwise a
            :class:`~loam.error.SectionError` is raised.
    """

    def __init__(self, **sections: Section):
        self._sections = []
        for sct_name, sct_meta in sections.items():
            if _is_valid(sct_name):
                setattr(self, sct_name, Section(**sct_meta.def_))
                self._sections.append(sct_name)
            else:
                raise error.SectionError(sct_name)
        self._parser = None
        self._nosub_valid = False
        self._config_files: Tuple[Path, ...] = ()

    @classmethod
    def from_dict_(
        cls, conf_dict: Mapping[str, Mapping[str, ConfOpt]]
    ) -> ConfigurationManager:
        """Use a dictionary to create a :class:`ConfigurationManager`.

        Args:
            conf_dict: the first level of keys are section names. The second
                level are option names. The values are the options metadata.

        Returns:
            a configuration manager with the requested sections and options.
        """
        return cls(**{name: Section(**opts)
                      for name, opts in conf_dict.items()})

    @property
    def config_files_(self) -> Tuple[Path, ...]:
        """Path of config files.

        The config files are in the order of reading. This means the most
        global config file is the first one on this list while the most local
        config file is the last one.
        """
        return self._config_files

    def set_config_files_(self, *config_files: Union[str, PathLike]) -> None:
        """Set the list of config files.

        Args:
            config_files: path of config files, given in the order
                of reading.
        """
        self._config_files = tuple(Path(path) for path in config_files)

    def __getitem__(self, sct: str) -> Section:
        return getattr(self, sct)

    def __delitem__(self, sct: str) -> None:
        delattr(self, sct)

    def __delattr__(self, sct: str) -> None:
        self[sct].reset_()

    def __getattr__(self, sct: str) -> None:
        raise error.SectionError(sct)

    def __iter__(self) -> Iterator[str]:
        return iter(self._sections)

    def __contains__(self, sct: str) -> bool:
        return sct in self._sections

    def sections_(self) -> Iterator[str]:
        """Iterate over configuration section names."""
        return iter(self)

    def options_(self) -> Iterator[Tuple[str, str]]:
        """Iterate over section and option names.

        This iterator is also implemented at the section level. The two loops
        produce the same output::

            for sct, opt in conf.options_():
                print(sct, opt)

            for sct in conf.sections_():
                for opt in conf[sct].options_():
                    print(sct, opt)
        """
        for sct in self:
            for opt in self[sct]:
                yield sct, opt

    def opt_vals_(self) -> Iterator[Tuple[str, str, Any]]:
        """Iterate over sections, option names, and option values.

        This iterator is also implemented at the section level. The two loops
        produce the same output::

            for sct, opt, val in conf.opt_vals_():
                print(sct, opt, val)

            for sct in conf.sections_():
                for opt, val in conf[sct].opt_vals_():
                    print(sct, opt, val)
        """
        for sct, opt in self.options_():
            yield sct, opt, self[sct][opt]

    def defaults_(self) -> Iterator[Tuple[str, str, Any]]:
        """Iterate over sections, option names, and option metadata.

        This iterator is also implemented at the section level. The two loops
        produce the same output::

            for sct, opt, meta in conf.defaults_():
                print(sct, opt, meta.default)

            for sct in conf.sections_():
                for opt, meta in conf[sct].defaults_():
                    print(sct, opt, meta.default)
        """
        for sct, opt in self.options_():
            yield sct, opt, self[sct].def_[opt]

    def reset_(self) -> None:
        """Restore default values of all options."""
        for sct, opt, meta in self.defaults_():
            self[sct][opt] = meta.default

    def create_config_(self, index: int = 0, update: bool = False) -> None:
        """Create config file.

        Create config file in :attr:`config_files_[index]`.

        Parameters:
            index: index of config file.
            update: if set to True and :attr:`config_files_` already exists,
                its content is read and all the options it sets are kept in the
                produced config file.
        """
        if not self.config_files_[index:]:
            return
        path = self.config_files_[index]
        if not path.parent.exists():
            path.parent.mkdir(parents=True)
        conf_dict: Dict[str, Dict[str, Any]] = {}
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

    def update_(self, conf_dict: Mapping[str, Mapping[str, Any]],
                conf_arg: bool = True) -> None:
        """Update values of configuration options with dict.

        Args:
            conf_dict: new values indexed by section and option names.
            conf_arg: if True, only options that can be set in a config file
                are updated.
        """
        for section, secdict in conf_dict.items():
            self[section].update_(secdict, conf_arg)

    def read_config_(self, cfile: Path) -> Optional[Mapping]:
        """Read a config file and set config values accordingly.

        Returns:
            content of config file.
        """
        if not cfile.exists():
            return {}
        try:
            conf_dict = toml.load(str(cfile))
        except toml.TomlDecodeError:
            return None
        self.update_(conf_dict)
        return conf_dict

    def read_configs_(self) -> Tuple[Dict[str, Dict[str, Any]], List[Path],
                                     List[Path]]:
        """Read config files and set config values accordingly.

        Returns:
            respectively content of files, list of missing/empty files and list
            of files for which a parsing error arised.
        """
        if not self.config_files_:
            return {}, [], []
        content: Dict[str, Dict[str, Any]] = {section: {} for section in self}
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
