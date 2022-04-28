"""Exceptions raised by loam."""


class LoamError(Exception):
    """Base class for exceptions raised by loam."""

    pass


class LoamWarning(UserWarning):
    """Warning category for warnings issued by loam."""

    pass


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
