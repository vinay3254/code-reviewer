#!/usr/bin/env bash
set -e

# Apply diff if non-empty patch file is present
if [ -f /tmp/patch.diff ] && [ -s /tmp/patch.diff ]; then
    patch -p1 < /tmp/patch.diff || git apply --reject /tmp/patch.diff || true
fi

# Run test command
TEST_CMD="${TEST_COMMAND:-pytest}"
coverage run -m pytest --json-report --json-report-file=/tmp/report.json > /tmp/stdout.log 2> /tmp/stderr.log || true
EXIT_CODE=$?

echo $EXIT_CODE > /tmp/exit_code.txt
cat /tmp/stdout.log
