from setuptools import setup, find_packages

setup(
    name="devopsx-python",
    packages=find_packages(),
    include_package_data=True,
    package_data={
        "devopsx": ["static/**/*", "media/logo.png"],
    },
)