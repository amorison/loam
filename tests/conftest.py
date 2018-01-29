import pytest

@pytest.fixture(scope='session', params=['confA'])
def conf_def(request):
    from loam.tools import ConfOpt
    metas = {}
    metas['confA'] = {
        'sectionA': {
            'optA': ConfOpt(1, True, None, {}, True, 'AA'),
            'optB': ConfOpt(2, True, None, {}, False, 'AB'),
            'optC': ConfOpt(3, True, None, {}, True, 'AC'),
        },
        'sectionB': {
            'optA': ConfOpt(4, True, None, {}, True, 'BA'),
            'optB': ConfOpt(5, True, None, {}, False, 'BB'),
            'optC': ConfOpt(6, False, None, {}, True, 'BC'),
        },
    }
    return metas[request.param]

@pytest.fixture
def conf(conf_def):
    from loam.manager import ConfigurationManager
    return ConfigurationManager(conf_def)

@pytest.fixture(params=['subsA'])
def sub_cmds(request):
    from loam.tools import Subcmd
    subs = {}
    subs['subsA'] = {
        None: Subcmd([], {}, 'subsA loam test'),
        '': Subcmd(['sectionA'], {}, None),
        'sectionB': Subcmd([], {}, 'sectionB subcmd help'),
    }
    return subs[request.param]
