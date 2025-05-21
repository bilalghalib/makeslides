from pathlib import Path
from setuptools import setup, find_packages

# Read long description from README
root = Path(__file__).parent
long_description = (root / "README.md").read_text(encoding="utf-8")

setup(
    name="makeslides",
    version="0.3.0",
    description="End-to-end pipeline: prompt → diagram → markdown → Google Slides",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="Bilal",
    packages=find_packages(exclude=("tests*", "examples*")),
    python_requires=">=3.9",
    install_requires=[
        "md2gslides>=3.1.0",
        "python-dotenv>=1.0.1",
        "google-auth>=2.28.0",
        "google-api-python-client>=2.122.0",
        "requests>=2.32.0",
        "beautifulsoup4>=4.12.3",
        "python-slugify>=8.0.4"
    ],
    entry_points={
        "console_scripts": [
            # High-level single command
            "makeslides = makeslides.__main__:cli_entry",
            # Keep backward-compat for your old one-shot scripts
            "diagram-render = makeslides.diagrams.renderer:cli_entry",
            "markdown-gen   = makeslides.markdown.generator:cli_entry",
            "slides-build   = makeslides.slides.builder:cli_entry",
        ]
    },
    include_package_data=True,   # so templates / configs bundled via MANIFEST.in later
    license="MIT",
    classifiers=[
        "Programming Language :: Python :: 3 :: Only",
        "License :: OSI Approved :: MIT License",
    ],
)

