from shlex import split
import pytest
import loam.error

def test_parser_not_built(conf):
    with pytest.raises(loam.error.ParserNotBuiltError):
        conf.parse_args_()

def test_parse_no_args(conf, sub_cmds):
    conf.build_parser_(sub_cmds)
    conf.parse_args_([])
    for s, o, m in conf.defaults_():
        assert conf[s][o] == m.default

def test_parse_nosub_common_args(conf, sub_cmds):
    conf.build_parser_(sub_cmds)
    conf.parse_args_(split('--optA 42'))
    assert conf.sectionA.optA == 42
    assert conf.sectionB.optA == 4

def test_parse_sub_common_args(conf, sub_cmds):
    conf.build_parser_(sub_cmds)
    conf.parse_args_(split('sectionB --optA 42'))
    assert conf.sectionA.optA == 1
    assert conf.sectionB.optA == 42

def test_parse_no_sub_only_args(conf, sub_cmds):
    conf.build_parser_(sub_cmds)
    conf.parse_args_(split('--optC 42 sectionB'))
    assert conf.sectionA.optC == 42
    assert conf.sectionB.optC == 6

def test_parse_not_conf_cmd_args(conf, sub_cmds):
    conf.build_parser_(sub_cmds)
    with pytest.raises(SystemExit):
        conf.parse_args_(split('sectionB --optC 42'))
