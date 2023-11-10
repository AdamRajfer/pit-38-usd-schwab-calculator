from setuptools import find_packages, setup

setup(
    name="charles_schwab",
    version="0.0.1",
    packages=find_packages(),
    include_package_data=True,
    package_data={"charles_schwab": ["config.yaml"]},
    entry_points={
        "console_scripts": ["charles_schwab=charles_schwab:charles_schwab"]
    },
    install_requires=["numpy", "pandas", "PyYAML"],
)
