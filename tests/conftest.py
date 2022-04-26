from dataclasses import dataclass
from pathlib import Path

import pytest

from loam.cli import Subcmd, CLIManager
from loam.tools import switch_opt
from loam.base import Entry, Section, Config


@dataclass
class SecA(Section):
    optA: int = Entry(val=1, doc="AA", cli_short='a').field()
    optB: int = Entry(val=2, doc="AB", in_file=False).field()
    optC: int = Entry(val=3, doc="AC").field()
    optBool: bool = switch_opt(True, 'o', 'Abool')


@dataclass
class SecB(Section):
    optA: int = Entry(val=4, doc="BA").field()
    optB: int = Entry(val=5, doc="BB", in_file=False).field()
    optC: int = Entry(val=6, doc="BC", in_cli=False).field()
    optBool: int = switch_opt(False, 'o', 'Bbool')


@dataclass
class Conf(Config):
    sectionA: SecA
    sectionB: SecB


@pytest.fixture
def conf() -> Conf:
    return Conf.default_()


@pytest.fixture(params=['subsA'])
def sub_cmds(request):
    subs = {}
    subs['subsA'] = {
        'common_': Subcmd('subsA loam test'),
        'bare_': Subcmd(None, 'sectionA'),
        'sectionB': Subcmd('sectionB subcmd help'),
    }
    return subs[request.param]


@pytest.fixture
def climan(conf, sub_cmds):
    return CLIManager(conf, **sub_cmds)


@pytest.fixture
def cfile(tmp_path):
    return tmp_path / 'config.toml'


@dataclass
class SectionA(Section):
    some_n: int = 42
    some_str: str = "foo"


@pytest.fixture
def section_a() -> SectionA:
    return SectionA()


@dataclass
class SectionB(Section):
    some_path: Path = Entry(val=Path(), to_str=str).field()
    some_str: str = Entry(val="bar", in_file=False).field()


@pytest.fixture
def section_b() -> SectionB:
    return SectionB()


@dataclass
class MyConfig(Config):
    section_a: SectionA
    section_b: SectionB


@pytest.fixture
def my_config() -> MyConfig:
    return MyConfig.default_()
