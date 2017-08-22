#!/usr/bin/env python
# -*- coding: utf-8 -*-

try:
    from setuptools import setup, find_packages
except ImportError:
    import ez_setup
    ez_setup.use_setuptools()
    from setuptools import setup, find_packages

VERSION = '0.1'

import os
def read(fname):
    return open(os.path.join(os.path.dirname(__file__), fname)).read()

setup(
    name='django-rdf-io',
    version = VERSION,
    description='Pluggable application for mapping elements of django models to an external RDF store',
    packages=['rdf_io'],
    include_package_data=True,
    author='Rob Atkinson',
    author_email='rob@metalinkage.com,au',
    license='BSD',
    long_description=read('README.md'),
    #download_url = "https://github.com/quinode/django-skosxl/tarball/%s" % (VERSION),
    #download_url='git://github.com/quinode/django-skosxl.git',
    zip_safe=False,
    install_requires = ['rdflib>=4.0',
                        'rdflib-jsonld',
                        'requests'
                        ]

)

