import toml


def test_config_files_setter(conf, cfile):
    assert conf.config_files_ == ()
    conf.set_config_files_(str(cfile))
    assert conf.config_files_ == (cfile,)


def test_create_config(conf, cfile):
    conf.set_config_files_(cfile)
    conf.create_config_()
    conf_dict = toml.load(str(cfile))
    assert conf_dict == {'sectionA': {'optA': 1, 'optC': 3, 'optBool': True},
                         'sectionB': {'optA': 4, 'optC': 6, 'optBool': False}}


def test_create_config_index(conf, cfile, nonexistent_file):
    conf.set_config_files_(nonexistent_file, cfile)
    conf.create_config_(index=1)
    conf_dict = toml.load(str(cfile))
    assert conf_dict == {'sectionA': {'optA': 1, 'optC': 3, 'optBool': True},
                         'sectionB': {'optA': 4, 'optC': 6, 'optBool': False}}


def test_create_config_no_update(conf, cfile):
    conf.set_config_files_(cfile)
    conf.sectionA.optA = 42
    conf.create_config_()
    conf_dict = toml.load(str(cfile))
    assert conf_dict == {'sectionA': {'optA': 1, 'optC': 3, 'optBool': True},
                         'sectionB': {'optA': 4, 'optC': 6, 'optBool': False}}


def test_create_config_update(conf, cfile):
    conf.set_config_files_(cfile)
    conf.sectionA.optA = 42
    conf.create_config_(update=True)
    conf_dict = toml.load(str(cfile))
    assert conf_dict == {'sectionA': {'optA': 42, 'optC': 3, 'optBool': True},
                         'sectionB': {'optA': 4, 'optC': 6, 'optBool': False}}


def test_read_config(conf, cfile):
    conf.set_config_files_(cfile)
    conf.create_config_()
    conf_dict = conf.read_config_(cfile)
    assert conf_dict == {'sectionA': {'optA': 1, 'optC': 3, 'optBool': True},
                         'sectionB': {'optA': 4, 'optC': 6, 'optBool': False}}


def test_read_config_missing(conf, cfile):
    assert conf.read_config_(cfile) == {}


def test_read_config_empty(conf, cfile):
    cfile.touch()
    assert conf.read_config_(cfile) == {}


def test_read_config_invalid(conf, illtoml):
    assert conf.read_config_(illtoml) is None


def test_read_configs(conf, cfile):
    conf.set_config_files_(cfile)
    conf.create_config_()
    conf_dict, empty, faulty = conf.read_configs_()
    assert empty == faulty == []
    assert conf_dict == {'sectionA': {'optA': 1, 'optC': 3, 'optBool': True},
                         'sectionB': {'optA': 4, 'optC': 6, 'optBool': False}}


def test_read_configs_missing_invalid(conf, nonexistent_file, illtoml):
    conf.set_config_files_(illtoml, nonexistent_file)
    conf_dict, empty, faulty = conf.read_configs_()
    assert empty == [nonexistent_file]
    assert faulty == [illtoml]
    assert conf_dict == {'sectionA': {}, 'sectionB': {}}
