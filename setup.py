from setuptools import setup, find_packages
import terra_stac_api


setup(
    name=terra_stac_api.__name__,
    version=terra_stac_api.__version__,
    author="Stijn Caerts",
    author_email="stijn.caerts@vito.be",
    description="Terra-STAC-API",
    packages=find_packages(),
    install_requires=[
        "stac-fastapi.elasticsearch==0.3.0",
        "python-jose==3.3.0"
    ],
    test_suite="tests",
    tests_require=[
        "pytest",
        "pytest-asyncio",
        "pytest-elasticsearch",
        "httpx"
    ]
)
