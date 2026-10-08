#!/bin/bash
set -euo pipefail

# Only run in Claude Code cloud sessions
if [ "${CLAUDE_CODE_REMOTE:-}" != "true" ]; then
  exit 0
fi

PLUGIN_DIR="$HOME/.claude/plugins/marketplaces/thedotmack"

# Install claude-mem once (idempotent: skipped if already installed)
if [ ! -d "$PLUGIN_DIR" ]; then
  npx --yes claude-mem@latest install
fi

# Start the worker (no-op if already running)
if ! curl -fsS -m 3 http://127.0.0.1:37700/api/health >/dev/null 2>&1; then
  npx --yes claude-mem start
fi
