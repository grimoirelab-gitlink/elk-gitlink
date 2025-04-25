import codecs
import os
import re

# Always prefer setuptools over distutils
from setuptools import setup

here = os.path.abspath(os.path.dirname(__file__))
readme_md = os.path.join(here, "README.md")

# Get the package description from the README.md file
with codecs.open(readme_md, encoding="utf-8") as f:
    long_description = f.read()

setup(
    name="grimoire-elk-gitlink",
    description="GrimoireLab library to produce gitlink indexes for ElasticSearch",
    long_description=long_description,
    long_description_content_type="text/markdown",
    version="0.1.0",
    license="GPLv3",
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Topic :: Software Development",
        "License :: OSI Approved :: GNU General Public License v3 or later (GPLv3+)",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.4",
        "Programming Language :: Python :: 3.5",
    ],
    keywords="development repositories analytics for gitlink",
    packages=[
        "grimoire_elk_gitlink",
        "grimoire_elk_gitlink.enriched",
        "grimoire_elk_gitlink.raw",
        # "grimoire_elk_gitlink.identities",
    ],
    entry_points={
        "grimoire_elk": "gitlink = grimoire_elk_gitlink.utils:get_connectors"
    },
    package_dir={"grimoire_elk_gitlink.enriched": "grimoire_elk_gitlink/enriched"},
    package_data={"grimoire_elk_gitlink.enriched": ["mappings/*.json"]},
    python_requires=">=3.4",
    setup_requires=["wheel"],
    extras_require={"sortinghat": ["sortinghat"], "mysql": ["PyMySQL"]},
    tests_require=["httpretty==0.8.6"],
    test_suite="tests",
    install_requires=[
        "grimoire-elk>=0.72.0",
        "perceval>=0.9.6",
        "perceval-gitlink>=0.1.0",
        "cereslib>=0.1.0",
        "grimoirelab-toolkit>=0.1.4",
        "sortinghat>=0.6.2",
        "graal>=0.2.2",
        "elasticsearch==6.3.1",
        "elasticsearch-dsl==6.3.1",
        "requests==2.26.0",
        "urllib3==1.26.5",
        "PyMySQL>=0.7.0",
        "geopy>=1.20.0",
        "statsmodels >= 0.9.0",
    ],
    zip_safe=False,
)
