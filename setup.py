from setuptools import setup, find_packages


setup(
    name="fox",
    version="0.1.0",
    description="Simple API to run commands on remote servers.",
    author="Daniel Kertesz",
    author_email="daniel@spatof.org",
    url="https://github.com/piger/fox",
    license="BSD-2-Clause",
    python_requires=">=3.6",
    install_requires=["asyncssh[libnacl]", "tqdm", "dataclasses;python_version<'3.7'"],
    tests_require=["pytest"],
    extras_require={
        "dev": ["tox", "pytest", "sphinx", "sphinx_rtd_theme"],
        "docs": ["sphinx", "sphinx_rtd_theme"],
    },
    packages=find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Environment :: Console",
        "Intended Audience :: Developers",
        "Intended Audience :: System Administrators",
        "License :: OSI Approved :: BSD License",
        "Operating System :: MacOS",
        "Operating System :: POSIX :: Linux",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Topic :: Internet",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: System :: Systems Administration",
    ],
)
