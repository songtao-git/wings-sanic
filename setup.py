# !/usr/bin/env python

import os
import sys

from setuptools import setup, find_packages

if sys.argv[-1] == 'publish':
    os.system("python setup.py sdist upload")
    sys.exit()

install_requires = [
    'six',
    'sanic',
    'Sanic-Cors',
]

setup(name='wings-sanic',
      version='0.6.0',
      description='The wings-sanic is a lightweight python framework aimed at making it as simple as possible to document your Sanic API with Swagger UI, Plus param validation and model serialization.',
      long_description='The wings-sanic is a lightweight python framework aimed at making it as simple as possible to document your Sanic API with Swagger UI, Plus param validation and model serialization.',
      author='SongTao',
      author_email='songtao@klicen.com',
      url='https://github.com/songtao-git/wings-sanic',
      packages=find_packages(),
      install_requires=install_requires,
      classifiers=[
          'Development Status :: 5 - Production/Stable',
          'Operating System :: MacOS',
          'Operating System :: POSIX :: Linux',
          'Topic :: System :: Software Distribution',
          'License :: OSI Approved :: MIT License',
          'Programming Language :: Python :: 3.7',
      ],
      include_package_data=True,
      )
