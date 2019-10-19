#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup

version = '1.0.'
try:
    circle_build_num = os.environ['CIRCLE_BUILD_NUM']
    version += circle_build_num
except KeyError:
    print("Couldn't find CIRCLE_BUILD_NUM, using 0 as minor instead")
    version += '0'

requirements = [
    'wheel',
    'PyYaml',
    'raven[flask]',
    'flask',
    'uWSGI==2.0.15',
]

setup(
    name='connectpy',
    version=version,
    description='Client-Server Connect5 Game',
    long_description='Client-Server Connect5 Game',
    author='Ciaran Gaffney',
    author_email='cgaffers@gmail.com',
    url='https://github.com/gaffer-93/connectpy',
    packages=['connectpy'],
    package_dir={'connectpy': 'src'},
    scripts=[
        'bin/connectpy_app.py',
    ],
    install_requires=requirements,
    dependency_links=[],
    test_suite='tests',
    include_package_data=True,
    zip_safe=False,
    keywords='connectpy',
    classifiers=[
    ],
)
