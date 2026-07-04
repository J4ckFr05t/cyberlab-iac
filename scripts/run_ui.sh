#!/usr/bin/env bash
# macOS: prevent SIGABRT when Streamlit forks ansible/terraform subprocesses.
export OBJC_DISABLE_INITIALIZE_FORK_SAFETY=YES

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
exec streamlit run "$ROOT/cyberlab_ui.py" "$@"
