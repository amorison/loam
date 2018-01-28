"""Exceptions raised by loam."""


class LoamError(Exception):

    """Base class for exceptions raised by loam."""

    pass


class SectionError(LoamError):

    """Raised when invalid config section is requested."""

    def __init__(self, section):
        """Initialization of instances:

        Args:
            section (str): invalid section name.

        Attributes:
            section (str): invalid section name.
        """
        self.section = section
        super().__init__('invalid section name: {}'.format(section))


class OptionError(LoamError):

    """Raised when invalid config option is requested."""

    def __init__(self, option):
        """Initialization of instances:

        Args:
            option (str): invalid option name.

        Attributes:
            option (str): invalid option name.
        """
        self.option = option
        super().__init__('invalid option name: {}'.format(option))


class ParserNotBuiltError(LoamError):

    """Raised when parse_args is called before build_parser"""

    pass
