from setuptools import setup

with open('README.rst') as rdm:
    README = rdm.read()

setup(
    name='loam',
    use_scm_version=True,

    description='Light configuration manager',
    long_description=README,

    url='https://github.com/amorison/loam',

    author='Adrien Morison',
    author_email='adrien.morison@gmail.com',

    license='MIT',
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3 :: Only',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        ],

    packages=['loam'],
    setup_requires=['setuptools_scm'],
    install_requires=['setuptools_scm'],
)
