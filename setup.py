#!/usr/bin/env python
"""
Setup script for SeedWatcher project
"""
from setuptools import setup, find_packages


setup(python_requires='>=3.7',
      name='SeedWatcher',
      version='1.0',
      description='Keep an eye on your seedbox (with or without raspberry pi)',
      author='Guillaume Peillex',
      author_email='guillaume.peillex@gmail.com',
      maintainer='Guillaume Peillex',
      maintainer_email='guillaume.peillex@gmail.com',
      url='https://github.com/hippo91/seed_watcher',
      packages=find_packages(),
      scripts=['seed_watcher.py'],
      install_requires=['aiohttp',],
      extras_require={'raspberry':['RPi.GPIO']}
     )