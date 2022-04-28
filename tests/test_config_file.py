import toml


def test_create_config(conf, cfile):
    conf.to_file_(cfile)
    conf_dict = toml.load(str(cfile))
    assert conf_dict == {'sectionA': {'optA': 1, 'optC': 3, 'optBool': True},
                         'sectionB': {'optA': 4, 'optC': 6, 'optBool': False}}


def test_create_config_no_update(conf, cfile):
    conf.sectionA.optA = 42
    conf.default_().to_file_(cfile)
    conf_dict = toml.load(str(cfile))
    assert conf_dict == {'sectionA': {'optA': 1, 'optC': 3, 'optBool': True},
                         'sectionB': {'optA': 4, 'optC': 6, 'optBool': False}}


def test_create_config_update(conf, cfile):
    conf.sectionA.optA = 42
    conf.to_file_(cfile)
    conf_dict = toml.load(str(cfile))
    assert conf_dict == {'sectionA': {'optA': 42, 'optC': 3, 'optBool': True},
                         'sectionB': {'optA': 4, 'optC': 6, 'optBool': False}}
