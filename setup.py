from setuptools import setup, find_packages
import os
import re

def get_metadata():
    metadata = {}
    init_path = os.path.join("stratos", "__init__.py")
    with open(init_path, "r") as f:
        content = f.read()
        for field in ["version", "app_name", "description", "author", "author_email", "url", "license"]:
            match = re.search(fr"__{field}__\s*=\s*['\"]([^'\"]+)['\"]", content)
            if match:
                metadata[field] = match.group(1)
    return metadata

meta = get_metadata()

setup(
    name=meta.get("app_name", "stratos-cli"),
    version=meta.get("version", "0.1"),
    description=meta.get("description", ""),
    long_description=open("README.md").read() if os.path.exists("README.md") else "",
    long_description_content_type="text/markdown",
    author=meta.get("author", ""),
    author_email=meta.get("author_email", ""),
    url=meta.get("url", ""),
    packages=find_packages(exclude=["tests*", "docs*"]),
    include_package_data=True,
    package_data={
        "stratos": ["assets/*"],
    },
    install_requires=[
        "google-generativeai",
        "google-genai",
        "python-dotenv",
        "rich",
        "readchar",
        "google-auth-oauthlib",
        "google-auth-httplib2",
        "duckduckgo-search"
    ],
    entry_points={
        "console_scripts": [
            "stratos=stratos.cli:main_entry",
        ],
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "Operating System :: OS Independent",
        "Environment :: Console",
    ],
    license=meta.get("license", "MIT"),
    python_requires='>=3.10',
)
