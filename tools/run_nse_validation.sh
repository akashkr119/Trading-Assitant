#!/usr/bin/env bash
set -euo pipefail

INTERVAL="${NSE_VALIDATION_INTERVAL:-60}"

if [[ -z "${GROWW_ACCESS_TOKEN:-}" && -z "${UPSTOX_ACCESS_TOKEN:-}" ]]; then
  echo "Set GROWW_ACCESS_TOKEN or UPSTOX_ACCESS_TOKEN before starting the NSE validator."
  exit 1
fi

export PYTHONUNBUFFERED=1
exec python tools/nse_validation_runner.py --interval "$INTERVAL"
