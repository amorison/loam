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
    return TupleEntry(int)


@pytest.fixture
def maybe_int():
    return MaybeEntry(int, none_to_toml="none")


@pytest.fixture
def maybe_path():
    return MaybeEntry(Path, str)


@dataclass
class Sec(Section):
    tpl: Tuple[int] = TupleEntry(int).entry()
    mfloat: Optional[float] = MaybeEntry(float).entry()
    mpath: Optional[Path] = MaybeEntry(Path, str).entry()


@dataclass
class Config(ConfigBase):
    sec: Sec


@pytest.fixture
def conf() -> Config:
    return Config.default_()


@pytest.fixture
def climan(conf) -> CLIManager:
    return CLIManager(conf, bare_=Subcmd("", "sec"))


def test_tuple_entry_int(tpl):
    assert tpl.from_toml("5, 6,7 ,1") == (5, 6, 7, 1)
    assert tpl.to_toml((3, 4, 5)) == (3, 4, 5)


def test_tuple_entry_from_invalid_type(tpl):
    with pytest.raises(TypeError):
        tpl.from_toml(8)


def test_tuple_entry_whitespace():
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


def test_tuple_entry_cli(conf, climan):
    assert conf.sec.tpl == ()
    climan.parse_args(shsplit("--tpl 1,2,3"))
    assert conf.sec.tpl == (1, 2, 3)


def test_maybe_entry_from_none(maybe_path, maybe_int):
    assert maybe_path.from_toml(None) is None
    assert maybe_path.from_toml("") is None
    assert maybe_int.from_toml(None) is None
    assert maybe_int.from_toml("none") is None


def test_maybe_entry_from_val(maybe_path, maybe_int):
    assert maybe_path.from_toml("foo/bar") == Path("foo/bar")
    assert maybe_path.from_toml(Path()) == Path()
    assert maybe_int.from_toml("2") == 2
    assert maybe_int.from_toml(42) == 42


def test_maybe_entry_none_to_toml(maybe_path, maybe_int):
    assert maybe_path.to_toml(None) == ""
    assert maybe_int.to_toml(None) == "none"


def test_maybe_entry_val_to_toml(maybe_path, maybe_int):
    assert maybe_path.to_toml(Path("foo/bar")) == "foo/bar"
    assert maybe_int.to_toml(5) == 5


def test_maybe_entry_cli_empty(conf, climan):
    conf.sec.mfloat = 1.0
    conf.sec.mpath = Path()
    climan.parse_args(shsplit("--mfloat --mpath"))
    assert conf.sec.mfloat is None
    assert conf.sec.mpath is None


def test_maybe_entry_cli_val(conf, climan):
    climan.parse_args(shsplit("--mfloat 3.14 --mpath foo/bar"))
    assert conf.sec.mfloat == 3.14
    assert conf.sec.mpath == Path("foo") / "bar"
