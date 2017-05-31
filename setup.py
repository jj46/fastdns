#!/usr/bin/env python
# -*- coding: utf-8 -*-

from setuptools import setup

with open('README.rst') as readme_file:
    readme = readme_file.read()

with open('HISTORY.rst') as history_file:
    history = history_file.read()

requirements = [
    'dnspython>=1.15.0',
    'pytest>=2.9.2',
    'requests>=2.13.0'
]

test_requirements = [
    'pytest>=3.0.7'
]

setup(
    name='fastdns',
    version='0.1.0',
    description="A library for performing many DNS queries very quickly",
    long_description=readme + '\n\n' + history,
    author="Joseph Williams",
    author_email='joseph.williams17@gmail.com',
    url='https://github.com/jj46/fastdns',
    packages=[
        'fastdns',
    ],
    package_dir={'fastdns':
                 'fastdns'},
    entry_points={
        'console_scripts': [
            'fastdns=fastdns.cli:main'
        ]
    },
    include_package_data=True,
    install_requires=requirements,
    license="MIT license",
    zip_safe=False,
    keywords='fastdns',
    classifiers=[
        'Development Status :: 2 - Pre-Alpha',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Natural Language :: English',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.5',
    ],
    test_suite='tests',
    tests_require=test_requirements
)
