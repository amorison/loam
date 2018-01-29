tools
=====

.. automodule:: loam.tools
   :members:
   :exclude-members: ConfOpt, Subcmd

   .. class:: ConfOpt

      :class:`collections.namedtuple` whose instances hold metadata of
      configuration options. It defines the following fields:

      - **default**: the default value of the configuration option.
      - **cmd_arg** (*bool*): whether the option is a command line argument.
      - **shortname** (*str*): short version of the command line argument.
      - **cmd_kwargs** (*dict*): keyword arguments fed to
        :meth:`argparse.ArgumentParser.add_argument` during the construction
        of the command line arguments parser.
      - **conf_arg** (*bool*): whether the option can be set in the config file.
      - **help** (*str*): short description of the option.

   .. class:: Subcmd

      :class:`collections.namedtuple` whose instances hold metadata of
      subcommand. It defines the following fields:

      - **extra_parsers** (*list*): list of section containing the options for
        this subcommand.
      - **defaults** (*dict*): values associated with the subcommand.
      - **help** (*str*): short description of the subcommand.
