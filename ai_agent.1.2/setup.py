#!/usr/bin/env python3
"""
Setup script for AI Helper
"""

from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="ai-helper",
    version="0.1.0",
    author="AI Helper Team",
    author_email="example@example.com",
    description="A local LLM-powered assistant that can interact with your macOS system",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/ai-helper",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: MacOS",
        "Development Status :: 3 - Alpha",
        "Intended Audience :: End Users/Desktop",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
    ],
    python_requires=">=3.8",
    install_requires=[
        "llama-cpp-python",
        "pyautogui",
        "pillow",
        "pytesseract",
        "rich",
    ],
    entry_points={
        "console_scripts": [
            "ai-helper=main:main",
        ],
    },
)
