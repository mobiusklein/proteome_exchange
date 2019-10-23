from setuptools import setup, find_packages


setup(
    name='proteome_exchange',
    version='0.0.1',
    description='A simple Proteome Exchange API',
    packages=find_packages(),
    install_requires=['lxml', 'six',]
)
