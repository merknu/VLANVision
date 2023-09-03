# Path: setup.py
#
from setuptools import setup, find_packages

with open("README.md", "r") as fh:
    long_description = fh.read()

with open("requirements.txt", "r") as f:
    requirements = f.read().splitlines()

setup(
    name="vlanvision",
    version="0.1.0",
    author="Knut Ingmar Merødningen",
    author_email="merknu@gmail.com",
    description="A network management software that simplifies managing networks with powerful integrations.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/merknu/vlanvision",
    packages=find_packages(),
    include_package_data=True,
    install_requires=requirements,
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Information Technology",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
    ],
    python_requires='>=3.6',
    entry_points={
        "console_scripts": [
            "vlanvision=vlanvision.main:main",
        ],
    },
)
