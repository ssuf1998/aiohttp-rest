import os
import re
from setuptools import setup


def read(path):
    with open(os.path.join(os.path.dirname(__file__), path), 'r') as f:
        data = f.read()
    return data.strip()


_version_re = re.compile(r'\s*__version__\s*=\s*\'(.*)\'\s*')
version = _version_re.findall(read('aiohttp_rest/__init__.py'))[0]


install_requires = read('requirements.txt').split('\n')
test_requires = read('build-requirements.txt').split('\n')
test_requires.extend(install_requires)

setup(
    name='aiohttp-rest',
    version=version,
    url='http://github.com/atbentley/aiohttp-rest/',
    license='MIT',
    author='Andrew Bentley',
    author_email='andrew.t.bentley@gmail.com',
    description='RESTful endpoints for aoihttp that bind directly to a model',
    long_description=read('README.rst'),
    packages=['aiohttp_rest'],
    include_package_data=True,
    zip_safe=False,
    platforms='any',
    install_requires=install_requires,
    tests_require=test_requires,
    classifiers=[
        'Development Status :: 4 - Beta',
        'Environment :: Web Environment',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3.5',
        'Topic :: Internet :: WWW/HTTP :: Dynamic Content',
        'Topic :: Software Development :: Libraries :: Python Modules'
    ]
)


