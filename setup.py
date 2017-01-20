#!/usr/bin/env python
# -*- coding: utf-8 -*-
import sys
from setuptools import setup
from setuptools.command.test import test as TestCommand


with open('README.rst') as readme_file:
    readme = readme_file.read()

with open('HISTORY.rst') as history_file:
    history = history_file.read()

requirements = [
    'prometheus-client>=0.0.13',
    'pyzabbix>=0.7.4',
    'PyYAML>=3.11',
    'click>=6.4',
]

test_requirements = [
    'pytest>=3.0.0',
    'pytest-localserver>=0.3.5',
    'pytest-cov>=2.4.0',
]


class PyTest(TestCommand):
    user_options = [('pytest-args=', 'a', "Arguments to pass to py.test")]

    def initialize_options(self):
        TestCommand.initialize_options(self)
        self.pytest_args = []

    def finalize_options(self):
        TestCommand.finalize_options(self)
        self.test_args = []
        self.test_suite = True

    def run_tests(self):
        import pytest
        errno = pytest.main(self.pytest_args)
        sys.exit(errno)


setup(
    name='zabbix_exporter',
    version='1.0.0',
    description="zabbix metrics for Prometheus",
    long_description=readme + '\n\n' + history,
    author="MyBook",
    author_email='coagulant@mybook.ru',
    url='https://github.com/Eksmo/zabbix-exporter',
    packages=['zabbix_exporter'],
    package_dir={'zabbix_exporter': 'zabbix_exporter'},
    include_package_data=True,
    install_requires=requirements,
    license="BSD",
    zip_safe=False,
    keywords='zabbix_exporter',
    entry_points="""
        [console_scripts]
        zabbix_exporter=zabbix_exporter:main
    """,
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',
        'Natural Language :: English',
        "Programming Language :: Python :: 2",
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        "Programming Language :: Python :: Implementation :: CPython",
        "Programming Language :: Python :: Implementation :: PyPy",
    ],
    test_suite='tests',
    tests_require=test_requirements,
    cmdclass={'test': PyTest},
)
