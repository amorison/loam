from dataclasses import dataclass
from pathlib import Path
from shlex import split as shsplit
from typing import Tuple

import pytest

from loam.base import Section, ConfigBase
from loam.cli import CLIManager, Subcmd
from loam.collections import TupleEntry


@pytest.fixture
def tpl():
    return TupleEntry(inner_from_toml=int)


@dataclass
class TplCliList(Section):
    tpl: Tuple[int] = TupleEntry(inner_from_toml=int).entry(
        default=[], in_cli_as="list")


@dataclass
class TplCliStr(Section):
    tpl: Tuple[int] = TupleEntry(inner_from_toml=int).entry(
        default=[], in_cli_as="str")


@dataclass
class ConfigCliList(ConfigBase):
    tplsec: TplCliList


@dataclass
class ConfigCliStr(ConfigBase):
    tplsec: TplCliStr


def test_tuple_entry_int(tpl):
    assert tpl.from_toml("5, 6,7,1") == (5, 6, 7, 1)
    assert tpl.to_toml((3, 4, 5)) == (3, 4, 5)


def test_tuple_entry_from_invalid_type(tpl):
    with pytest.raises(TypeError):
        tpl.from_toml(8)


def test_tuple_entry_from_str_whitespace():
    tpl = TupleEntry(inner_from_toml=int, str_sep="")
    assert tpl.from_toml("5  6 7\t1\n  42") == (5, 6, 7, 1, 42)


def test_tuple_entry_from_arr_str(tpl):
    assert tpl.from_toml(["5", "3", "42"]) == (5, 3, 42)


def test_tuple_entry_from_str_no_sep():
    tpl = TupleEntry(inner_from_toml=int, str_sep=None)
    with pytest.raises(TypeError):
        tpl.from_toml("42,41")
    tpl.from_toml([42, 41]) == (42, 41)


def test_tuple_entry_path():
    root = Path("path")
    tpl = TupleEntry(inner_from_toml=Path, inner_to_toml=str)
    assert tpl.from_toml(["path/1", "path/2"]) == (root / "1", root / "2")
    assert tpl.to_toml((root, root / "subdir")) == ("path", "path/subdir")


def test_tuple_entry_nested(tpl):
    tpl = TupleEntry.wrapping(tpl, str_sep=".")
    expected = ((3,), (4, 5), (6,))
    assert tpl.from_toml("3.4,5.6") == expected
    assert tpl.from_toml(["3", [4, 5], [6]]) == expected
    assert tpl.from_toml(expected) == expected
    assert tpl.to_toml(expected) == expected


def test_tuple_entry_cli_as_invalid(tpl):
    with pytest.raises(ValueError):
        tpl.entry([], in_cli_as="invalid")


def test_tuple_entry_cli_as_list():
    conf = ConfigCliList.default_()
    assert conf.tplsec.tpl == tuple()
    climan = CLIManager(conf, bare_=Subcmd("", "tplsec"))
    climan.parse_args(shsplit("--tpl 1 2 3"))
    assert conf.tplsec.tpl == (1, 2, 3)


def test_tuple_entry_cli_as_str():
    conf = ConfigCliStr.default_()
    assert conf.tplsec.tpl == tuple()
    climan = CLIManager(conf, bare_=Subcmd("", "tplsec"))
    climan.parse_args(shsplit("--tpl 1,2,3"))
    assert conf.tplsec.tpl == (1, 2, 3)
