from pathlib import Path

import pytest

from loam.manager import ConfOpt, Section, ConfigurationManager
from loam.cli import Subcmd, CLIManager

@pytest.fixture(scope='session', params=['confA'])
def conf_def(request):
    metas = {}
    metas['confA'] = {
        'sectionA': Section(
            optA=ConfOpt(1, True, None, {}, True, 'AA'),
            optB=ConfOpt(2, True, None, {}, False, 'AB'),
            optC=ConfOpt(3, True, None, {}, True, 'AC'),
        ),
        'sectionB': Section(
            optA=ConfOpt(4, True, None, {}, True, 'BA'),
            optB=ConfOpt(5, True, None, {}, False, 'BB'),
            optC=ConfOpt(6, False, None, {}, True, 'BC'),
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
def cfile(tmpdir):
    return Path(str(tmpdir)) / 'config.toml'

@pytest.fixture
def nonexistent_file(tmpdir):
    return Path(str(tmpdir)) / 'dummy.toml'

@pytest.fixture
def illtoml(tmpdir):
    path = Path(str(tmpdir)) / 'ill.toml'
    with path.open('w') as ift:
        ift.write('not}valid[toml\n')
    return path
