#!/usr/bin/env bash
set -euo pipefail

python -m build
printf 'ORBIT package artifacts:\n'
ls -lh dist/
