"""Easy config management setup for your Python project."""

try:
    from ._version import version as __version__
except ImportError:
    __version__ = 'unknown'
