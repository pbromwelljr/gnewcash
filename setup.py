import os
from setuptools import find_packages, setup


def read(file_name):
    return open(os.path.join(os.path.dirname(__file__), file_name)).read()


setup(
    name='gnewcash',
    version='PLACEHOLDER',
    description='Python Library for reading, interacting with, and writing GnuCash files',
    author='Paul Bromwell Jr.',
    author_email='pbromwelljr@gmail.com',
    packages=find_packages(exclude=('tests',)),
    license='MIT',
    keywords='gnucash finance finances cash personal banking',
    url='https://github.com/pbromwelljr/gnewcash',
    long_description=read('README.md'),
    long_description_content_type='text/markdown',
    classifiers=[
        'Development Status :: 4 - Beta',
        'Topic :: Office/Business :: Financial :: Accounting',
        'License :: OSI Approved :: MIT License',
        'Intended Audience :: Financial and Insurance Industry',
        'Natural Language :: English',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3.11',
        'Programming Language :: Python :: 3.12',
    ]
)
