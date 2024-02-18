from setuptools import find_packages, setup

setup(
    name="pit-38-usd-schwab-calculator",
    version="0.0.1",
    packages=find_packages(),
    install_requires=["hydra-core", "numpy", "pandas", "yfinance"],
)
