from setuptools import setup, find_packages

setup(
    name="dqa_test_tool",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "pyserial",
        "PySide6",
    ],
    package_data={
        'core': ['*'],
        'gui': ['*'],
        'util': ['*'],
    },
) 