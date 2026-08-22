#!/usr/bin/env bash
set -euo pipefail

# Keep the crypto validation monitor alive in a Codespace/terminal session.
# The runner performs one scan every 5 minutes and records outcomes locally.
INTERVAL="${CRYPTO_VALIDATION_INTERVAL:-300}"

if ! [[ "$INTERVAL" =~ ^[0-9]+$ ]] || (( INTERVAL < 60 )); then
  echo "CRYPTO_VALIDATION_INTERVAL must be an integer >= 60 seconds." >&2
  exit 2
fi

mkdir -p reports

echo "Starting Crypto Engine Validation monitor"
echo "Interval: ${INTERVAL}s"
echo "Journal: reports/crypto_validation_journal.csv"
echo "Press Ctrl+C to stop."

echo

python tools/crypto_validation_runner.py --interval "$INTERVAL"
