import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="CSMCAsm-sarchar",
    version="0.1.0-beta",
    author="Chuck",
    author_email="chuck+csbcasm@borboggle.com",
    description="Cross-platform assembler for 65C816",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/sarchar/CSBCAsm",
    packages=setuptools.find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Development Status :: 2 - Pre-Alpha",
        "Environment :: Console",
        "Intended Audience :: Developers",
        "Operating System :: OS Independent",
        "Topic :: Software Development :: Assemblers",
    ],
    python_requires='>=3.5',
    install_requires=[
        "rply==0.7.7"
    ],
    entry_points={
        'console_scripts': [
            'csbcasm = CSBCAsm.tools:main',
        ],
    },
    test_suite="tests",
)
