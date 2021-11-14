import pytest

from loam.manager import ConfOpt, Section, ConfigurationManager
from loam.cli import Subcmd, CLIManager
from loam.tools import switch_opt


@pytest.fixture(scope='session', params=['confA'])
def conf_def(request):
    metas = {}
    metas['confA'] = {
        'sectionA': Section(
            optA=ConfOpt(1, True, 'a', {}, True, 'AA'),
            optB=ConfOpt(2, True, None, {}, False, 'AB'),
            optC=ConfOpt(3, True, None, {}, True, 'AC'),
            optBool=switch_opt(True, 'o', 'Abool'),
        ),
        'sectionB': Section(
            optA=ConfOpt(4, True, None, {}, True, 'BA'),
            optB=ConfOpt(5, True, None, {}, False, 'BB'),
            optC=ConfOpt(6, False, None, {}, True, 'BC'),
            optBool=switch_opt(False, 'o', 'Bbool'),
        ),
    }
    return metas[request.param]


@pytest.fixture
def conf(conf_def):
    return ConfigurationManager(**conf_def)


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


@pytest.fixture
def nonexistent_file(tmp_path):
    return tmp_path / 'dummy.toml'


@pytest.fixture
def illtoml(tmp_path):
    path = tmp_path / 'ill.toml'
    path.write_text('not}valid[toml\n')
    return path
