First steps
===========

Installation
------------

The loam package is available on PyPI, you can install it with pip::

    python3 -m pip install -U --user loam

It is compatible with Python 3.4 and above.

Basic usage
-----------

The following code is a very simple example showing how to use loam to create a
configuration object with no config file nor argument parsing management.

::

    from loam.manager import ConfigurationManager
    from loam.tools import bare_opt

    # A simple dictionary define all the options and their default values.
    # The first level of keys are the section names, the second level of keys
    # are the option names. Note that you can have the same option name living
    # in two different sections.
    conf_def = {
        'sectionA': {'optionA': bare_opt('foo'),
                     'optionB': bare_opt(42),
                     'optionC': bare_opt('bar')},
        'sectionB': {'optionD': bare_opt(None),
                     'optionA': bare_opt(3.14156)}
    }

    conf = ConfigurationManager(conf_def)

    # you can access options value with attribute or item notation
    assert conf.sectionA.optionA is conf.sectionA['optionA']
    assert conf.sectionA is conf['sectionA']

    # you can set values (with attribute or item notation)
    conf.sectionA.optionA = 'baz'
    # and then reset it to its default value
    del conf.sectionA.optionA
    assert conf.sectionA.optionA == 'foo'
    # you can also reset entire sections at once
    del conf.sectionA
    # or even all configuration options (note that all methods of
    # ConfigurationManager have a postfixed _ to minimize the risk of collision
    # with your section or option names).
    conf.reset_()
