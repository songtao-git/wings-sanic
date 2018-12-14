# !/usr/bin/env python

from setuptools import setup, find_packages

install_requires = [
    'six',
    'sanic',
    'Sanic-Cors',
]

tests_require = []

setup(name='wings-sanic',
      version='0.1.1',
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
          'Programming Language :: Python :: 3.5',
          'Programming Language :: Python :: 3.6',
          'Programming Language :: Python :: 3.7',
      ]
      )
