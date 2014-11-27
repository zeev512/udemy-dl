#!/usr/bin/env python

import subprocess
from distutils.core import setup

requirements = [pkg.split('=')[0] for pkg in open('requirements.txt').readlines()]

description = 'Download videos from Udemy for personal offline use'
try:
    subprocess.call(["pandoc", "README.md", "-f", "markdown", "-t", "rst", "-o", "README.rst"])
    long_description = open("README.rst").read()
except OSError:
    print("Pandoc not installed")
    long_description = description

classifiers = ['Environment :: Console',
               'Programming Language :: Python :: 2',
               'Programming Language :: Python :: 3',
               'Topic :: Multimedia :: Video',
               ]

version = open('CHANGES.txt').readlines()[0][1:].strip()

setup(name='udemy-dl',
      version=version,
      description=description,
      author='Gaganpreet Singh Arora',
      author_email='gaganpreet.arora@gmail.com',
      url='https://github.com/gaganpreet/udemy-dl',
      scripts=['src/udemy-dl',],
      install_requires=requirements,
      long_description=long_description,
      packages=['udemy_dl'],
      package_dir = {'udemy_dl': 'src/udemy_dl'},
      classifiers=classifiers
    )
