#!/usr/bin/env bash

set -euo pipefail

apt-get update
apt-get install --yes --no-install-recommends curl jq

for command_name in bash curl jq awk mktemp; do
  command -v "$command_name"
done
command -v sha256sum >/dev/null || command -v shasum >/dev/null

python -m pip install --no-cache-dir --require-hashes -r matcher/requirements.lock
python -m pip check

python -W error::ResourceWarning - <<'PY'
import sys
import unittest

suite = unittest.defaultTestLoader.discover("matcher/tests")
discovered = suite.countTestCases()
result = unittest.TextTestRunner(verbosity=2).run(suite)
print(
    "matcher tests: discovered=%d run=%d skipped=%d"
    % (discovered, result.testsRun, len(result.skipped)),
    flush=True,
)
if not result.wasSuccessful():
    sys.exit(1)
if result.testsRun != discovered:
    sys.exit("not every discovered matcher test ran")
if result.skipped:
    sys.exit("matcher tests were skipped")
PY
