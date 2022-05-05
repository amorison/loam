from dataclasses import dataclass
from pathlib import Path
from shlex import split as shsplit
from typing import Optional, Tuple

import pytest

from loam.base import Section, ConfigBase
from loam.cli import CLIManager, Subcmd
from loam.collections import MaybeEntry, TupleEntry


@pytest.fixture
def tpl():
    return TupleEntry(inner_from_toml=int)


@dataclass
class SecA(Section):
    tpl_list: Tuple[int] = TupleEntry(inner_from_toml=int).entry(
        default=[], in_cli_as="list")
    mfloat: Optional[float] = MaybeEntry(float).entry(default=None)


@dataclass
class SecB(Section):
    tpl_str: Tuple[int] = TupleEntry(inner_from_toml=int).entry(
        default=[], in_cli_as="str")
    mpath: Optional[Path] = MaybeEntry(Path, str).entry(default=None)


@dataclass
class Config(ConfigBase):
    sec_a: SecA
    sec_b: SecB


@pytest.fixture
def conf() -> Config:
    return Config.default_()


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


def test_tuple_entry_cli_as_list(conf):
    assert conf.sec_a.tpl_list == tuple()
    climan = CLIManager(conf, bare_=Subcmd("", "sec_a"))
    climan.parse_args(shsplit("--tpl_list 1 2 3"))
    assert conf.sec_a.tpl_list == (1, 2, 3)


def test_tuple_entry_cli_as_str(conf):
    assert conf.sec_b.tpl_str == tuple()
    climan = CLIManager(conf, bare_=Subcmd("", "sec_b"))
    climan.parse_args(shsplit("--tpl_str 1,2,3"))
    assert conf.sec_b.tpl_str == (1, 2, 3)


def test_maybe_entry_cli_empty(conf):
    climan = CLIManager(conf, bare_=Subcmd("", "sec_a", "sec_b"))
    conf.sec_a.mfloat = 1.0
    conf.sec_b.mpath = Path()
    climan.parse_args(shsplit("--mfloat --mpath"))
    assert conf.sec_a.mfloat is None
    assert conf.sec_b.mpath is None


def test_maybe_entry_cli_val(conf):
    climan = CLIManager(conf, bare_=Subcmd("", "sec_a", "sec_b"))
    climan.parse_args(shsplit("--mfloat 3.14 --mpath foo/bar"))
    assert conf.sec_a.mfloat == 3.14
    assert conf.sec_b.mpath == Path("foo") / "bar"
