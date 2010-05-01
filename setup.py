# -*- coding: utf-8 -*-
from distutils.core import setup

long_desc = open('README').read()

setup(
    name='karnickel',
    version='0.1',
    url='http://dev.pocoo.org/',
    download_url='http://pypi.python.org/pypi/karnickel',
    license='BSD',
    author='Georg Brandl',
    author_email='georg@python.org',
    description='Python macros using the AST',
    long_description=long_desc,
    zip_safe=False,
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Topic :: Utilities',
    ],
    platforms='any',
    py_modules=['karnickel'],
)
