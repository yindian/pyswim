#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
from setuptools import setup, find_packages
import sys

try:
    import xapian
except:
    print 'SWIM needs xapian to build search index, please install it:'
    print '  http://www.xapian.org/'
    sys.exit(1)

setup(
    name='pyswim',
    version='0.2',
    description='Static WIkipedia Mirror',
    long_description='Static WIkipedia Mirror by Python',
    author='Xie Yanbo',
    author_email='xieyanbo@gmail.com',
    license='BSD',
    url='http://pyswim.googlecode.com',
    download_url='http://pyswim.googlecode.com',
    classifiers=[
        'Development Status :: 2 - Pre-Alpha',
        'Environment :: Console',
        'Environment :: Web Environment',
        'Framework :: Django',
        'License :: OSI Approved :: GNU General Public License (GPL)',
        'Operating System :: POSIX :: Linux',
        'Programming Language :: Python',
        'Topic :: Education',
        ],
    zip_safe=False,
    install_requires=['django', 'mwlib>=0.2.7.dev'],
    py_modules=['swim', 'mywiki'],
    packages=find_packages(),
)
