from setuptools import Extension, setup, find_packages
from distutils.command.build_ext import build_ext
from distutils.sysconfig import get_python_inc
from codecs import open
from os import path
import numpy as np

here = path.abspath(path.dirname(__file__))

try:
    execfile
except NameError:

    def execfile(fname, globs, locs=None):
        locs = locs or globs
        exec(compile(open(fname).read(), fname, "exec"), globs, locs)


version_ns = {}
try:
    execfile(path.join(here, "_version.py"), version_ns)
except EnvironmentError:
    version = "dev"
else:
    version = version_ns.get("__version__", "dev")

setup(
    author="Georgina Kennedy",
    author_email="georgina.kennedy@unsw.edu.au",
    description="CaVa-specific spacy language",
    name="cava_lang",
    python_requires=">=3.10",
    version=version,
    packages=find_packages(exclude=["ez_setup", "example", "test"]),
    include_package_data=True,
    install_requires=[
        'spacy>=3.4', 
        'medspacy>=1.1',
        'striprtf',
        'python-dateutil'
        ],
    extras_require={
        "dev": ["pytest>=3.7", "pytest-timeout>=1.4.2", "check-manifest>=0.43"],
        "gpu": ["spacy[cuda114]>=3.4", "spacy-transformers"],
    },
)
