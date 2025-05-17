from setuptools import setup, find_packages

setup(
    name="rtclient",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "python-dotenv",
        "scipy",
        "pydantic",
        "azure-core",
        "aiohttp",
        "azure-identity",
        "ruff",
        "black",
        "soundfile",
        "numpy",
        "pytest",
        "pytest-asyncio",
        "openai",
    ]
)