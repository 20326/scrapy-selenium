"""This module contains the packaging routine for the pybook package"""
import sys
import pip
from setuptools import setup, find_packages

try:
    if pip.__version__ >= "19.3":
        from pip._internal.req import parse_requirements
        from pip._internal.network.session import PipSession
    elif pip.__version__ >= "10.0" and pip.__version__ < "19.3":
        from pip._internal.req import parse_requirements
        from pip._internal.download import PipSession
    else:  # pip < 10 is not supported
        raise Exception('Please upgrade pip: pip install --upgrade pip')
except ImportError as err:  # for future changes in pip
    print('New breaking changes in pip!!', err)
    sys.exit()

# TOOD
# install_requirements = [str(ir.req) for ir in parse_requirements('requirements/requirements.txt', session=PipSession())]


setup(
    packages=find_packages(),
    # install_requires=install_requirements,
)
