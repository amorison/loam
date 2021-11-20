"""Exceptions raised by loam."""


class LoamError(Exception):
    """Base class for exceptions raised by loam."""

    pass


class LoamWarning(UserWarning):
    """Warning category for warnings issued by loam."""

    pass


class SectionError(LoamError):
    """Raised when invalid config section is requested.

    Args:
        section: invalid section name.

    Attributes:
        section: invalid section name.
    """

    def __init__(self, section: str):
        self.section = section
        super().__init__(f'invalid section name: {section}')


class OptionError(LoamError):
    """Raised when invalid config option is requested.

    Args:
        option: invalid option name.

    Attributes:
        option: invalid option name.
    """

    def __init__(self, option: str):
        self.option = option
        super().__init__(f'invalid option name: {option}')


class SubcmdError(LoamError):
    """Raised when an invalid Subcmd name is requested.

    Args:
        option: invalid subcommand name.

    Attributes:
        option: invalid subcommand name.
    """

    def __init__(self, option: str):
        self.option = option
        super().__init__(f'invalid subcommand name: {option}')
