#!/usr/bin/env bash
set -euo pipefail

DAW_REPO="${DAW_REPO:-https://github.com/gio0z/daw-flow.git}"
DAW_REF="${DAW_REF:-main}"
TMP_DIR=""

cleanup() {
  if [ -n "$TMP_DIR" ] && [ -d "$TMP_DIR" ]; then
    rm -rf "$TMP_DIR"
  fi
}
trap cleanup EXIT

if ! command -v python3 >/dev/null 2>&1; then
  echo "error: python3 (>= 3.10) is required." >&2
  exit 1
fi

SCRIPT_DIR=""
if [ -n "${BASH_SOURCE[0]:-}" ] && [ -f "${BASH_SOURCE[0]}" ]; then
  SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
fi

if [ -n "${DAW_SOURCE_DIR:-}" ]; then
  if [ ! -f "$DAW_SOURCE_DIR/scripts/install.py" ]; then
    echo "error: DAW_SOURCE_DIR does not contain scripts/install.py: $DAW_SOURCE_DIR" >&2
    exit 1
  fi
  SUITE_DIR="$DAW_SOURCE_DIR"
elif [ -n "$SCRIPT_DIR" ] && [ -f "$SCRIPT_DIR/scripts/install.py" ]; then
  SUITE_DIR="$SCRIPT_DIR"
else
  if ! command -v git >/dev/null 2>&1; then
    echo "error: git is required to fetch deterministic-agentic-workflow." >&2
    exit 1
  fi
  TMP_DIR="$(mktemp -d)"
  git clone --quiet --depth 1 --branch "$DAW_REF" "$DAW_REPO" "$TMP_DIR/daw"
  SUITE_DIR="$TMP_DIR/daw"
fi

if [ "$#" -eq 0 ]; then
  if [ -t 0 ]; then
    python3 "$SUITE_DIR/scripts/install.py" --interactive
  elif [ -t 1 ] && [ -r /dev/tty ]; then
    python3 "$SUITE_DIR/scripts/install.py" --interactive < /dev/tty
  else
    python3 "$SUITE_DIR/scripts/install.py" install --agent all --scope user
  fi
else
  python3 "$SUITE_DIR/scripts/install.py" "$@"
fi
