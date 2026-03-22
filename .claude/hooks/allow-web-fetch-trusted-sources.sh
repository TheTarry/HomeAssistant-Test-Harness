#!/usr/bin/env bash
set -euo pipefail

# ── Allowed URL prefixes ────────────────────────────────────────────────────
ALLOWED_PREFIXES=(
  "https://github.com/home-assistant"
  "https://raw.githubusercontent.com/home-assistant"
)
# ───────────────────────────────────────────────────────────────────────────

input=$(cat)

tool_name=$(echo "$input" | jq -r '.tool_name // empty')
if [[ "$tool_name" != "WebFetch" ]]; then
  exit 0
fi

url=$(echo "$input" | jq -r '.tool_input.url // empty')
if [[ -z "$url" ]]; then
  exit 0
fi

for prefix in "${ALLOWED_PREFIXES[@]}"; do
  if [[ "$url" == "${prefix}"* ]]; then
    echo '{"decision": "allow", "reason": "URL matches allowed prefix"}'
    exit 0
  fi
done

# No match — fall back to Claude Code's default permission behaviour
exit 0
