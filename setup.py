from setuptools import find_packages, setup

setup(
    name="pit-38-usd-schwab-calculator",
    version="0.0.1",
    packages=find_packages(),
    entry_points={
        "console_scripts": [
            "pit_38_usd_schwab_calculator=pit_38_usd_schwab_calculator:pit_38_usd_schwab_calculator"
        ]
    },
    install_requires=["numpy", "pandas"],
)
