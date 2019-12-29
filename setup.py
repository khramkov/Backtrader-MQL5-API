import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="backtradermql5",
    version="1.31",
    author="Nikolai Khramkov",
    # author_email="khramkov@example.com",
    description="Python Backtrader - Metaquotes MQL5 - API",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/khramkov/Backtrader-MQL5-API",
    packages=setuptools.find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.6',
    keywords=['trading', 'development'],
)