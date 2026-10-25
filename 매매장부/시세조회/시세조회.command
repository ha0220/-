#!/bin/bash
cd "$(dirname "$0")"
echo
echo "=== Stock price helper ==="
if command -v python3 >/dev/null 2>&1; then
  python3 fetch_prices.py "$@"
else
  echo "Python 3 is not installed. Install it from https://www.python.org/downloads/"
fi
echo
read -n 1 -s -r -p "Press any key to close..."
