"""Easy config management setup for your Python project."""

from setuptools_scm import get_version
from pkg_resources import get_distribution, DistributionNotFound

try:
    __version__ = get_version(root='..', relative_to=__file__)
except LookupError:
    __version__ = get_distribution('loam').version
except (DistributionNotFound, ValueError):
    __version__ = 'unknown'
