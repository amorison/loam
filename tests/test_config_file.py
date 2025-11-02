from __future__ import annotations

import sys
from typing import TYPE_CHECKING

if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib

if TYPE_CHECKING:
    from pathlib import Path

    from conftest import Conf


def test_create_config(conf: Conf, cfile: Path) -> None:
    conf.to_file_(cfile)
    with cfile.open("rb") as tomlf:
        conf_dict = tomllib.load(tomlf)
    assert conf_dict == {
        "sectionA": {"optA": 1, "optC": 3, "optBool": True},
        "sectionB": {"optA": 4, "optC": 6, "optBool": False},
    }


def test_create_config_no_update(conf: Conf, cfile: Path) -> None:
    conf.sectionA.optA = 42
    conf.default_().to_file_(cfile)
    with cfile.open("rb") as tomlf:
        conf_dict = tomllib.load(tomlf)
    assert conf_dict == {
        "sectionA": {"optA": 1, "optC": 3, "optBool": True},
        "sectionB": {"optA": 4, "optC": 6, "optBool": False},
    }


def test_create_config_update(conf: Conf, cfile: Path) -> None:
    conf.sectionA.optA = 42
    conf.to_file_(cfile)
    with cfile.open("rb") as tomlf:
        conf_dict = tomllib.load(tomlf)
    assert conf_dict == {
        "sectionA": {"optA": 42, "optC": 3, "optBool": True},
        "sectionB": {"optA": 4, "optC": 6, "optBool": False},
    }
