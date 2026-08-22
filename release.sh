#!/usr/bin/env bash
set -euo pipefail

rm -rf dist build
python -m pip install --upgrade build
python -m build
python -m pip install --force-reinstall --no-deps dist/*.whl
orbit --help >/dev/null
printf 'ORBIT release artifacts validated successfully.\n'
