import loam.tools


def test_set_conf_str(conf):
    loam.tools.set_conf_str(conf, ['sectionB.optA=42', 'sectionA.optBool=f'])
    assert conf.sectionB.optA == 42
    assert conf.sectionA.optBool is False
