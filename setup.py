#!/usr/bin/env python

"""The setup script."""

from setuptools import setup, find_packages

with open('README.md') as readme_file:
    readme = readme_file.read()

with open('HISTORY.rst') as history_file:
    history = history_file.read()

requirements = ['numpy', 'pandas', 'pyimagej', 'bg-atlasapi']

test_requirements = [ ]

setup(
    author="Nicolas Chiaruttini",
    author_email='nicolas.chiaruttini@epfl.ch',
    python_requires='>=3.6',
    classifiers=[
        'Development Status :: 2 - Pre-Alpha',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: GNU General Public License v3 (GPLv3)',
        'Natural Language :: English',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8'
    ],
    description="Aligning Big Brains and Atlases, controlled from Python.",
    install_requires=requirements,
    license="GNU General Public License v3",
    #long_description=readme + '\n\n' + history,
    long_description=readme,
    long_description_content_type='text/markdown',
    include_package_data=True,
    keywords='abba_python',
    name='abba_python',
    packages=['abba_python', 'abba_python.abba_private'], #find_packages(include=['abba_python', 'abba_python.*', 'abba_python/abba_private']),
    test_suite='tests',
    tests_require=test_requirements,
    url='https://github.com/BIOP/abba_python',
    version='0.8.0',
    zip_safe=False,
)
