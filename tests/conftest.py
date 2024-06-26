from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from pytest import FixtureRequest, fixture

from loam.base import ConfigBase, Section, entry
from loam.cli import CLIManager, Subcmd
from loam.tools import path_entry, switch_opt


@dataclass
class SecA(Section):
    optA: int = entry(val=1, doc="AA", cli_short="a")
    optB: int = entry(val=2, doc="AB", in_file=False)
    optC: int = entry(val=3, doc="AC")
    optBool: bool = switch_opt(True, "o", "Abool")


@dataclass
class SecB(Section):
    optA: int = entry(val=4, doc="BA")
    optB: int = entry(val=5, doc="BB", in_file=False)
    optC: int = entry(val=6, doc="BC", in_cli=False)
    optBool: int = switch_opt(False, "o", "Bbool")


@dataclass
class Conf(ConfigBase):
    sectionA: SecA
    sectionB: SecB


@fixture
def conf() -> Conf:
    return Conf.default_()


@fixture(params=["subsA"])
def sub_cmds(request: FixtureRequest) -> dict[str, Subcmd]:
    subs = {}
    subs["subsA"] = {
        "common_": Subcmd("subsA loam test"),
        "bare_": Subcmd("bare command help", "sectionA"),
        "sectionB": Subcmd("sectionB subcmd help"),
    }
    return subs[request.param]


@fixture
def climan(conf: Conf, sub_cmds: dict[str, Subcmd]) -> CLIManager:
    return CLIManager(conf, **sub_cmds)


@fixture
def cfile(tmp_path: Path) -> Path:
    return tmp_path / "config.toml"


@dataclass
class SectionA(Section):
    some_n: int = 42
    some_str: str = "foo"


@fixture
def section_a() -> SectionA:
    return SectionA()


@dataclass
class SectionB(Section):
    some_path: Path = path_entry(".", "")
    some_str: str = entry(val="bar", in_file=False)


@fixture
def section_b() -> SectionB:
    return SectionB()


@dataclass
class SectionNotInFile(Section):
    some_int: int = entry(val=0, in_file=False)
    some_str: str = entry(val="baz", in_file=False)


@dataclass
class MyConfig(ConfigBase):
    section_a: SectionA
    section_b: SectionB
    section_not_in_file: SectionNotInFile


@fixture
def my_config() -> MyConfig:
    return MyConfig.default_()
