#!/bin/bash
# Opens the ledger (the .html file next to this script) in Chrome (or the default browser).
cd "$(dirname "$0")"
f=$(ls *.html 2>/dev/null | head -n 1)
if [ -z "$f" ]; then
  echo "No .html file was found next to this script."
  read -n 1 -s -r -p "Press any key to close..."
  exit 1
fi
open -a "Google Chrome" "$f" 2>/dev/null || open "$f"
