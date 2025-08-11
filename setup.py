#!/usr/bin/env python3
"""
Setup script for EasySize - Telegram Bot for Body Measurement Tracking
"""

from pathlib import Path

from setuptools import find_packages, setup

# Read the README file
this_directory = Path(__file__).parent
readme_file = this_directory / "README.md"
if readme_file.exists():
    long_description = readme_file.read_text(encoding="utf-8")
else:
    long_description = "Telegram bot for tracking body measurements"

# Read requirements
requirements = []
requirements_file = this_directory / "requirements.txt"
if requirements_file.exists():
    requirements = [
        req.strip()
        for req in requirements_file.read_text().strip().split("\n")
        if req.strip() and not req.startswith("#")
    ]

# Package metadata
setup(
    name="easy-track",
    version="1.0.0",
    author="EasySize Team",
    author_email="contact@EasySize.bot",
    description="Telegram bot for tracking body measurements",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/easy-track",
    package_dir={"": "src"},
    packages=find_packages(where="src"),
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: End Users/Desktop",
        "Topic :: Communications :: Chat",
        "Topic :: Internet :: WWW/HTTP :: Dynamic Content",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Operating System :: OS Independent",
        "Framework :: AsyncIO",
        "Environment :: Console",
    ],
    python_requires=">=3.11",
    install_requires=requirements,
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "pytest-asyncio>=0.20.0",
            "black>=23.0.0",
            "flake8>=6.0.0",
            "mypy>=1.0.0",
            "pre-commit>=3.0.0",
        ],
        "test": [
            "pytest>=7.0.0",
            "pytest-asyncio>=0.20.0",
            "pytest-cov>=4.0.0",
            "factory-boy>=3.2.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "easy-track=easy_track.bot:main",
            "easy-track-bot=easy_track.bot:main",
        ],
    },
    include_package_data=True,
    package_data={
        "easy_track": [
            "*.ini",
            "*.sql",
            "alembic/*.py",
            "alembic/**/*.py",
            "alembic/**/*.mako",
        ],
    },
    zip_safe=False,
    keywords=[
        "telegram",
        "bot",
        "fitness",
        "tracking",
        "measurements",
        "body",
        "health",
        "async",
        "postgresql",
        "sqlalchemy",
    ],
    project_urls={
        "Bug Reports": "https://github.com/yourusername/easy-track/issues",
        "Source": "https://github.com/yourusername/easy-track",
        "Documentation": "https://github.com/yourusername/easy-track#readme",
    },
)
