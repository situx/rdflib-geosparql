from setuptools import setup


def get_version():
    from pathlib import Path

    with open(Path(__file__).parent / "geosparql" / "__init__.py") as file_:
        for line in file_.readlines():
            if line.startswith("__version__"):
                return line.split('"')[1]


setup(
    name="geosparql",
    version=get_version(),
    description="GeoSPARQL functions implemented as SPARQL extension in RDFLib",
    long_description=open("README.md", encoding="utf-8").read(),
    long_description_content_type="text/markdown",
    maintainer="Timo Homburg",
    maintainer_email="timo.homburg@gmx.de",
    url="https://github.com/rdflib/rdflib-geosparql",
    license="BSD",
    packages=["geosparql"],
    platforms=["any"],
    classifiers=[
        "Programming Language :: Python",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "License :: OSI Approved :: BSD License",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Operating System :: OS Independent",
        "Natural Language :: English",
    ],
    test_suite="tests",
    install_requires=["rdflib>=6.0.0", "shapely","fastkml","pygml"],
    tests_require=["pytest"],
)
