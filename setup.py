#!/usr/bin/env python3
"""
Setup script for MCP Academic Editor
"""

from setuptools import setup, find_packages
from pathlib import Path

# Read the README file
this_directory = Path(__file__).parent
long_description = (this_directory / "README.md").read_text()

# Read requirements
requirements = []
with open("requirements.txt") as f:
    requirements = [line.strip() for line in f if line.strip() and not line.startswith("#")]

setup(
    name="mcp-academic-editor",
    version="1.0.0",
    author="Jeffrey Vadala",
    author_email="jeffrey.vadala@example.com",
    description="Surgical manuscript editing with word count protection via Model Context Protocol",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/jeffreyvadala/mcp-academic-editor",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Researchers",
        "Intended Audience :: Education",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Scientific/Engineering",
        "Topic :: Text Processing",
        "Topic :: Education",
    ],
    python_requires=">=3.9",
    install_requires=requirements,
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "pytest-asyncio>=0.21.0", 
            "black>=23.0.0",
            "isort>=5.12.0",
            "mypy>=1.5.0",
        ],
        "docs": [
            "mkdocs>=1.5.0",
            "mkdocs-material>=9.0.0",
        ],
        "nlp": [
            "nltk>=3.8.0",
            "spacy>=3.7.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "mcp-academic-editor=server:main",
        ],
    },
    include_package_data=True,
    package_data={
        "src": ["*.py"],
        "examples": ["*.md", "*.json"],
        "docs": ["*.md"],
    },
    keywords=[
        "academic writing",
        "manuscript editing", 
        "word count protection",
        "surgical editing",
        "mcp",
        "model context protocol",
        "anthropology",
        "research",
    ],
)