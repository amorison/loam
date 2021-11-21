from shlex import split
import pytest
import loam.error
import loam.cli


def test_parse_no_args(conf, climan):
    climan.parse_args([])
    for s, o, m in conf.defaults_():
        assert conf[s][o] == m.default


def test_parse_nosub_common_args(conf, climan):
    climan.parse_args(split('--optA 42'))
    assert conf.sectionA.optA == 42
    assert conf.sectionB.optA == 4


def test_parse_short_nosub_common_args(conf, climan):
    climan.parse_args(split('-a 42'))
    assert conf.sectionA.optA == 42
    assert conf.sectionB.optA == 4


def test_parse_switch_nosub_common_args(conf, climan):
    climan.parse_args(split('-optBool'))
    assert conf.sectionA.optBool is False
    assert conf.sectionB.optBool is False


def test_parse_switch_short_nosub_common_args(conf, climan):
    climan.parse_args(split('-o'))
    assert conf.sectionA.optBool is False
    assert conf.sectionB.optBool is False


def test_parse_sub_common_args(conf, climan):
    climan.parse_args(split('sectionB --optA 42'))
    assert conf.sectionA.optA == 1
    assert conf.sectionB.optA == 42


def test_parse_switch_sub_common_args(conf, climan):
    climan.parse_args(split('sectionB +optBool'))
    assert conf.sectionA.optBool is True
    assert conf.sectionB.optBool is True


def test_parse_switch_short_sub_common_args(conf, climan):
    climan.parse_args(split('sectionB +o'))
    assert conf.sectionA.optBool is True
    assert conf.sectionB.optBool is True


def test_parse_no_sub_only_args(conf, climan):
    climan.parse_args(split('--optC 42 sectionB'))
    assert conf.sectionA.optC == 3
    assert conf.sectionB.optC == 6


def test_parse_not_conf_cmd_args(climan):
    with pytest.raises(SystemExit):
        climan.parse_args(split('sectionB --optC 42'))


def test_build_climan_invalid_sub(conf):
    with pytest.raises(loam.error.SubcmdError):
        loam.cli.CLIManager(conf, **{'1invalid_sub': loam.cli.Subcmd('')})
