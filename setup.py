import os
from setuptools import setup


def read(file_name):
    return open(os.path.join(os.path.dirname(__file__), file_name)).read()


setup(
    name='gnewcash',
    version='0.1',
    description='Python Library for reading, interacting with, and writing GnuCash files',
    author='Paul Bromwell Jr.',
    author_email='pbromwelljr@outlook.com',
    packages=[],
    license='MIT',
    keywords='gnucash finance finances cash personal banking',
    url='http://packages.python.org/gnewcash',
    long_description=read('README.md'),
    classifiers=[
        'Development Status :: 2 - Pre-Alpha',
        'Topic :: Finances',
        'License :: OSI Approved :: MIT License',
    ]
)
