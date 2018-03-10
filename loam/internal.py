"""Internal objects.

You should not use these in your own script.
"""

import re
import shlex
import subprocess


def zsh_version():
    """Try to guess zsh version, returns (0, 0) on failure."""
    try:
        out = str(subprocess.check_output(shlex.split('zsh --version')))
    except (FileNotFoundError, subprocess.CalledProcessError):
        return (0, 0)
    match = re.search('[0-9]+\.[0-9]+', out)
    return tuple(map(int, match[0].split('.'))) if match else (0, 0)
