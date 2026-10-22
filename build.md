### Version
Package version is derived from git tags by setuptools-scm. Tag `v0.19.8` becomes version `0.19.8`.
Do not set the version in source files.

Release by tagging and pushing; CI builds and publishes:

```bash
git tag v0.20.0
git push origin v0.20.0
```

A build that is not on a tag gets a dev version such as `0.20.1.dev3+gabc1234`.
PyPI rejects local versions (the `+...` suffix), so publish from a clean tagged commit.
Building requires git history and tags (`git fetch --tags`). `pip install -e .` writes
`src/suprsend/_version.py` (gitignored).

### Build and upload
Setup a python3 virtualenv `venv_sdk` for building this lib.
```bash
virtualenv -p python3 venv_sdk
source venv_sdk/bin/activate
python3 -m pip install --upgrade build
python3 -m pip install --upgrade twine
```
Test locally
```sh
pip install -e .
```
Build package
```bash
python3 -m build
# On test.pypi.org
python3 -m twine upload --repository testpypi dist/*
# On pypi.org
python3 -m twine upload dist/*
```
Installing newly uploaded package 
```bash
python3 -m pip install --index-url https://test.pypi.org/simple/ --no-deps suprsend-py-sdk
```
