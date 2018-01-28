import pytest
import loam.error

def test_get_subconfig(conf, conf_def):
    for sub in conf_def:
        assert getattr(conf, sub) is conf[sub]

def test_get_opt(conf):
    for sub, opt in conf.options_():
        assert getattr(conf[sub], opt) is conf[sub][opt]

def test_get_invalid_subconfig(conf):
    invalid = 'invalidsubdummy'
    with pytest.raises(loam.error.SectionError) as err:
        _ = conf[invalid]
    assert err.value.section == invalid

def test_get_invalid_opt(conf):
    invalid = 'invalidoptdummy'
    for sub in conf:
        with pytest.raises(loam.error.OptionError) as err:
            _ = conf[sub][invalid]
        assert err.value.option == invalid

def test_contains_section(conf, conf_def):
    for sub in conf_def:
        assert sub in conf

def test_contains_option(conf, conf_def):
    for sub, opts in conf_def.items():
        for opt in opts:
            assert opt in conf[sub]

def test_contains_invalid_section(conf):
    assert 'invalidsubdummy' not in conf

def test_contains_invalid_option(conf):
    assert 'invalidoptdummy' not in conf.sectionA

def test_reset_all(conf):
    conf.sectionA.optA = 42
    conf.reset_()
    assert conf.sectionA.optA == 1

def test_reset_subconfig(conf):
    conf.sectionA.optA = 42
    del conf.sectionA
    assert conf.sectionA.optA == 1

def test_reset_subconfig_item(conf):
    conf.sectionA.optA = 42
    del conf['sectionA']
    assert conf.sectionA.optA == 1

def test_reset_opt(conf):
    conf.sectionA.optA = 42
    del conf.sectionA.optA
    assert conf.sectionA.optA == 1

def test_reset_opt_item(conf):
    conf.sectionA.optA = 42
    del conf.sectionA['optA']
    assert conf.sectionA.optA == 1

def test_config_iter_subs(conf, conf_def):
    raw_iter = set(iter(conf))
    subs_iter = set(conf.subs_())
    subs_expected = set(conf_def.keys())
    assert raw_iter == subs_iter == subs_expected

def test_config_iter_options(conf, conf_def):
    options_iter = set(conf.options_())
    options_expected = set((sub, opt) for sub in conf_def
                           for opt in conf_def[sub])
    assert options_iter == options_expected

def test_config_iter_default_val(conf):
    vals_iter = set(conf.opt_vals_())
    vals_dflts = set((s, o, m.default) for s, o, m in conf.defaults_())
    assert vals_iter == vals_dflts

def test_config_iter_subconfig(conf, conf_def):
    raw_iter = set(iter(conf.sectionA))
    opts_iter = set(conf.sectionA.options_())
    opts_expected = set(conf_def['sectionA'].keys())
    assert raw_iter == opts_iter == opts_expected

def test_config_iter_subconfig_default_val(conf):
    vals_iter = set(conf.sectionA.opt_vals_())
    vals_dflts = set((o, m.default) for o, m in conf.sectionA.defaults_())
    assert vals_iter == vals_dflts
