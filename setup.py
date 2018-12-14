# !/usr/bin/env python
import os

from setuptools import setup, find_packages

base = os.path.dirname(os.path.abspath(__file__))

README_PATH = os.path.join(base, "README.md")

install_requires = [
    'six',
    'sanic',
    'Sanic-Cors',
]

tests_require = []

setup(name='wings-sanic',
      version='0.1.0',
      description='wings-sanic is lightweight python framework for sainc',
      long_description=open(README_PATH).read(),
      author='SongTao',
      author_email='songtao@klicen.com',
      url='https://github.com/songtao/wings-sanic/',
      packages=find_packages(),
      install_requires=install_requires,
      classifiers=[
          'Development Status :: 5 - Production/Stable',
          'Operating System :: MacOS',
          'Operating System :: POSIX :: Linux',
          'Topic :: System :: Software Distribution',
          'License :: OSI Approved :: MIT License',
          'Programming Language :: Python :: 3.5+'
      ]
      )
