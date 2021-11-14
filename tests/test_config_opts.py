import pytest
import loam.error
import loam.manager


def test_build_from_dict(conf, conf_def):
    conf_dict = {name: dict(sct.def_) for name, sct in conf_def.items()}
    conf_fd = loam.manager.ConfigurationManager.from_dict_(conf_dict)
    assert all(conf[s][o] == conf_fd[s][o]
               for s in conf_def for o in conf_def[s])


def test_build_section_invalid_option_name():
    invalid_id = 'not a valid id'
    with pytest.raises(loam.error.OptionError) as err:
        loam.manager.Section(**{invalid_id: 'dummy'})
    assert err.value.option == invalid_id


def test_build_manager_invalid_section_name():
    invalid_id = 'not a valid id'
    with pytest.raises(loam.error.SectionError) as err:
        loam.manager.ConfigurationManager(**{invalid_id: 'dummy'})
    assert err.value.section == invalid_id


def test_get_subconfig(conf, conf_def):
    for sub in conf_def:
        assert getattr(conf, sub) is conf[sub]


def test_get_opt(conf):
    for sub, opt in conf.options_():
        assert getattr(conf[sub], opt) is conf[sub][opt]


def test_set_opt_def(conf):
    with pytest.raises(TypeError):
        conf.sectionA.def_['optA'] = None


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


def test_reset_subconfig_func(conf):
    conf.sectionA.optA = 42
    conf.sectionA.reset_()
    assert conf.sectionA.optA == 1


def test_reset_opt(conf):
    conf.sectionA.optA = 42
    del conf.sectionA.optA
    assert conf.sectionA.optA == 1


def test_reset_opt_item(conf):
    conf.sectionA.optA = 42
    del conf.sectionA['optA']
    assert conf.sectionA.optA == 1


def test_update_opt(conf):
    conf.sectionA.update_({'optA': 42, 'optC': 43})
    assert conf.sectionA.optA == 42 and conf.sectionA.optC == 43


def test_update_section(conf):
    conf.update_({'sectionA': {'optA': 42}, 'sectionB': {'optA': 43}})
    assert conf.sectionA.optA == 42 and conf.sectionB.optA == 43


def test_update_opt_conf_arg(conf):
    conf.sectionA.update_({'optB': 42})
    assert conf.sectionA.optB == 2
    conf.sectionA.update_({'optB': 42}, conf_arg=False)
    assert conf.sectionA.optB == 42


def test_update_section_conf_arg(conf):
    conf.update_({'sectionA': {'optB': 42}, 'sectionB': {'optB': 43}})
    assert conf.sectionA.optB == 2 and conf.sectionB.optB == 5
    conf.update_({'sectionA': {'optB': 42}, 'sectionB': {'optB': 43}},
                 conf_arg=False)
    assert conf.sectionA.optB == 42 and conf.sectionB.optB == 43


def test_opt_def_values(conf, conf_def):
    assert all(conf[s].def_[o] == conf_def[s].def_[o]
               for s in conf_def for o in conf_def[s])


def test_config_iter_subs(conf, conf_def):
    raw_iter = set(iter(conf))
    scts_iter = set(conf.sections_())
    scts_expected = set(conf_def.keys())
    assert raw_iter == scts_iter == scts_expected


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
    opts_expected = set(conf_def['sectionA'])
    assert raw_iter == opts_iter == opts_expected


def test_config_iter_subconfig_default_val(conf):
    vals_iter = set(conf.sectionA.opt_vals_())
    vals_dflts = set((o, m.default) for o, m in conf.sectionA.defaults_())
    assert vals_iter == vals_dflts


def test_context_section(conf):
    with conf.sectionA.context_(optA=42, optBool=False):
        assert conf.sectionA.optA == 42
        assert conf.sectionA.optBool is False
    assert conf.sectionA.optA == 1
    assert conf.sectionA.optBool is True
