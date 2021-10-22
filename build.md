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
