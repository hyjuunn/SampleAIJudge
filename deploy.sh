rm -rf dist build lib/*.egg-info
python setup.py bdist_wheel
twine upload -r pypi dist/*
rm -rf dist build lib/*.egg-info