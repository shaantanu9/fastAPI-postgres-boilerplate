from setuptools import setup, find_packages

setup(
    name="app",
    version="0.1.0",
    packages=find_packages(include=["app", "app.*"]),
    install_requires=[
        "fastapi>=0.110.0",
        "uvicorn>=0.27.0",
        "sqlalchemy>=2.0.0",
        "pydantic>=2.0.0",
        "python-jose>=3.3.0",
        "passlib>=1.7.4",
        "python-multipart>=0.0.9",
        "redis>=5.0.0",
        "httpx>=0.24.1",
        "loguru>=0.7.2",
        "PyJWT>=2.8.0",
    ],
    python_requires=">=3.9",
) 