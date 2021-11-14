# Configuration file for the Sphinx documentation builder.
#
# This file only contains a selection of the most common options. For a full
# list see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Path setup --------------------------------------------------------------

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.

import os
import sys
from pkg_resources import get_distribution

sys.path.insert(0, os.path.abspath('..'))

import loam

html_theme = 'sphinx_rtd_theme'

# -- General configuration ------------------------------------------------

# If your documentation needs a minimal Sphinx version, state it here.
needs_sphinx = '4.0'

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom
# ones.
extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.napoleon',
]

root_doc = 'index'

autodoc_member_order = 'bysource'
autoclass_content = 'both'

# -- Project information -----------------------------------------------------
project = 'loam'
copyright = '2018 - 2021, Adrien Morison'
author = 'Adrien Morison'

# The full version, including alpha/beta/rc tags.
release = get_distribution("loam").version
# The short X.Y version.
version = '.'.join(release.split('.')[:2])

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
exclude_patterns = ['_build']

# The name of the Pygments (syntax highlighting) style to use.
pygments_style = 'sphinx'


# -- Options for HTML output ----------------------------------------------

# Output file base name for HTML help builder.
htmlhelp_basename = 'loamdoc'


# -- Options for LaTeX output ---------------------------------------------

# Grouping the document tree into LaTeX files. List of tuples
# (source start file, target name, title,
#  author, documentclass [howto, manual, or own class]).
latex_documents = [
    (root_doc, 'loam.tex', 'loam Documentation',
     'Adrien Morison', 'manual'),
]


# -- Options for manual page output ---------------------------------------

# One entry per manual page. List of tuples
# (source start file, name, description, authors, manual section).
man_pages = [
    (root_doc, 'loam', 'loam Documentation',
     [author], 1)
]


# -- Options for Texinfo output -------------------------------------------

# Grouping the document tree into Texinfo files. List of tuples
# (source start file, target name, title, author,
#  dir menu entry, description, category)
texinfo_documents = [
    (root_doc, 'loam', 'loam Documentation',
     author, 'loam', 'One line description of project.',
     'Miscellaneous'),
]
