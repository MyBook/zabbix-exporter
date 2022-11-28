import os
import re
import setuptools

with open('README.md') as readme_file:
    readme = readme_file.read()

with open('HISTORY.rst') as history_file:
    history = history_file.read()

with open('requirements.txt') as reqs_file:
    requirements = reqs_file.readlines()


def get_version(package):
    """
    Return package version as listed in `__version__` in `init.py`.
    """
    init_py = open(os.path.join(package, '__init__.py')).read()
    return re.search("__version__ = ['\"]([^'\"]+)['\"]", init_py).group(1)


setuptools.setup(
    name='zabbix_selective_exporter',
    version=get_version('zabbix_exporter'),
    url='https://github.com/qoollo/zabbix-exporter',
    packages=setuptools.find_packages(),
    install_requires=requirements,
    python_requires='>=3.6',

    description="zabbix metrics for Prometheus",
    long_description_content_type="text/markdown",
    long_description=readme + '\n\n' + history,

    author="MyBook, Qoollo",
    author_email='kirill.kazakov@qoollo.com',
    license="BSD",

    keywords='zabbix_exporter',
    entry_points="""
        [console_scripts]
        zabbix_exporter=zabbix_exporter:main
    """,
    classifiers=[
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
    ],
)