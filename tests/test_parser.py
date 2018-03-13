from shlex import split
import pytest
import loam.error

def test_parse_no_args(conf, climan):
    climan.parse_args([])
    for s, o, m in conf.defaults_():
        assert conf[s][o] == m.default

def test_parse_nosub_common_args(conf, climan):
    climan.parse_args(split('--optA 42'))
    assert conf.sectionA.optA == 42
    assert conf.sectionB.optA == 4

def test_parse_sub_common_args(conf, climan):
    climan.parse_args(split('sectionB --optA 42'))
    assert conf.sectionA.optA == 1
    assert conf.sectionB.optA == 42

def test_parse_no_sub_only_args(conf, climan):
    climan.parse_args(split('--optC 42 sectionB'))
    assert conf.sectionA.optC == 42
    assert conf.sectionB.optC == 6

def test_parse_not_conf_cmd_args(climan):
    with pytest.raises(SystemExit):
        climan.parse_args(split('sectionB --optC 42'))
