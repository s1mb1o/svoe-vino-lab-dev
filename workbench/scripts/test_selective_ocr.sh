#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/../.."
export OPENBLAS_NUM_THREADS=1
export VECLIB_MAXIMUM_THREADS=1
"${PYTHON:-python3}" -m unittest discover -s matcher/tests -p 'test*ocr*.py' -v
