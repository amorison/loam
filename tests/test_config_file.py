from __future__ import annotations

from typing import TYPE_CHECKING

import toml

if TYPE_CHECKING:
    from pathlib import Path

    from conftest import Conf


def test_create_config(conf: Conf, cfile: Path) -> None:
    conf.to_file_(cfile)
    conf_dict = toml.load(str(cfile))
    assert conf_dict == {
        "sectionA": {"optA": 1, "optC": 3, "optBool": True},
        "sectionB": {"optA": 4, "optC": 6, "optBool": False},
    }


def test_create_config_no_update(conf: Conf, cfile: Path) -> None:
    conf.sectionA.optA = 42
    conf.default_().to_file_(cfile)
    conf_dict = toml.load(str(cfile))
    assert conf_dict == {
        "sectionA": {"optA": 1, "optC": 3, "optBool": True},
        "sectionB": {"optA": 4, "optC": 6, "optBool": False},
    }


def test_create_config_update(conf: Conf, cfile: Path) -> None:
    conf.sectionA.optA = 42
    conf.to_file_(cfile)
    conf_dict = toml.load(str(cfile))
    assert conf_dict == {
        "sectionA": {"optA": 42, "optC": 3, "optBool": True},
        "sectionB": {"optA": 4, "optC": 6, "optBool": False},
    }
