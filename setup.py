import os
from setuptools import setup, find_packages


def read(file_name):
    return open(os.path.join(os.path.dirname(__file__), file_name)).read()


setup(
    name='gnewcash',
    version='1.0.0',
    description='Python Library for reading, interacting with, and writing GnuCash files',
    author='Paul Bromwell Jr.',
    author_email='pbromwelljr@gmail.com',
    packages=find_packages(),
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
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
    ]
)
