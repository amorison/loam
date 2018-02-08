tools
=====

.. automodule:: loam.tools
   :members:
   :exclude-members: Subcmd

   .. class:: Subcmd

      :class:`collections.namedtuple` whose instances hold metadata of
      subcommand. It defines the following fields:

      - **extra_parsers** (*list*): list of section containing the options for
        this subcommand.
      - **defaults** (*dict*): values associated with the subcommand.
      - **help** (*str*): short description of the subcommand.
