from pathlib import Path
from setuptools import setup


setup(
    name='loam',

    description='Light configuration manager',
    long_description=Path("README.rst").read_text(),

    url='https://github.com/amorison/loam',

    author='Adrien Morison',
    author_email='adrien.morison@gmail.com',

    license='MIT',
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3 :: Only',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
    ],

    packages=['loam'],
    package_data={'loam': ['py.typed']},

    python_requires=">=3.7",
    install_requires=[
        'setuptools_scm>=6.2',
        'toml>=0.10.2',
    ],
)
