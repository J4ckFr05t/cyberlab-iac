#!/usr/bin/env python3
import os
import sys

# macOS: Streamlit loads ObjC; fork() in subprocess without this aborts the parent (SIGABRT).
if sys.platform == "darwin":
    os.environ.setdefault("OBJC_DISABLE_INITIALIZE_FORK_SAFETY", "YES")

import html
import re
import subprocess
import json
import shutil
import tempfile
import time
from datetime import timedelta

try:
    import streamlit as st
    import streamlit.components.v1 as components
except ImportError:
    print("Missing dependency: streamlit. Install with: pip install -r requirements.txt", file=sys.stderr)
    raise

try:
    import yaml
except ImportError:
    print("Missing dependency: PyYAML (import yaml). Install with: pip install -r requirements.txt", file=sys.stderr)
    raise

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TERRAFORM_DIR = os.path.join(BASE_DIR, "terraform")
ANSIBLE_DIR = os.path.join(BASE_DIR, "ansible")
CYBERLAB_DIR = os.path.join(BASE_DIR, ".cyberlab")
PLAYBOOKS_JOB_DIR = os.path.join(CYBERLAB_DIR, "playbooks")
BATCH_PLAYBOOK_KEY = "batch"
DEPLOY_LOG = os.path.join(CYBERLAB_DIR, "deploy.log")
DEPLOY_STATUS_FILE = os.path.join(CYBERLAB_DIR, "deploy.status.json")
DEPLOY_EXIT_FILE = os.path.join(CYBERLAB_DIR, "deploy.exit")
CLEAN_HOSTS_SCRIPT = os.path.join(BASE_DIR, "scripts", "clean_known_hosts.sh")

TEMPLATES = [
    "ubuntu-server-template",
    "ubuntu-desktop-template",
    "win11-template",
    "win-dc-2022-template",
]

PLAYBOOKS = [
    ("check_connectivity.yml", "Check Connectivity", "#3fb950"),
    ("dc_setup.yml", "Domain Controller Setup", "#58a6ff"),
    ("join_to_domain.yml", "Join to Domain", "#58a6ff"),
    ("siem_stack.yml", "SIEM Stack (ELK & Fleet)", "#d2a8ff"),
    ("enroll_elastic_agents.yml", "Enroll Elastic Agents", "#d2a8ff"),
    ("setup_wazuh.yml", "Wazuh Manager Setup", "#f0883e"),
    ("enroll_wazuh_agents.yml", "Enroll Wazuh Agents", "#f0883e"),
    ("setup_thehive.yml", "TheHive & SOC Manager", "#f778ba"),
    ("wazuh_thehive_integration.yml", "Wazuh-TheHive Integration", "#f778ba"),
    ("suricata_setup.yml", "Suricata IDS on SOC-01", "#ff7b72"),
]

THEME_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500;700&family=Inter:wght@400;500;600;700&display=swap');

:root {
    --bg: #0d1117;
    --bg-elevated: #161b22;
    --text: #e6edf3;
    --text-muted: #8b949e;
    --accent: #3fb950;
    --accent-dim: #238636;
    --danger: #f85149;
    --bg-card: rgba(22, 27, 34, 0.7);
    --border: rgba(48, 54, 61, 0.9);
}

/* Unified app background */
.stApp, [data-testid="stAppViewContainer"], [data-testid="stHeader"],
section[data-testid="stMain"], section[data-testid="stMain"] > div {
    background-color: var(--bg) !important;
}

[data-testid="stSidebar"] {
    background: var(--bg) !important;
    border-right: 1px solid var(--border) !important;
}

[data-testid="stSidebar"] [data-testid="stRadio"] > label { display: none !important; }

[data-testid="stSidebar"] [data-testid="stRadio"] [role="radiogroup"] {
    gap: 0px !important;
}

[data-testid="stSidebar"] [data-testid="stRadio"] label[data-baseweb="radio"] {
    background: transparent !important;
    border-left: 3px solid transparent;
    border-radius: 0 6px 6px 0 !important;
    padding: 14px 16px !important;
    margin: 0 !important;
    transition: all 0.15s ease;
    cursor: pointer !important;
    width: 100% !important;
    display: flex !important;
    min-height: 48px !important;
    align-items: center !important;
}

[data-testid="stSidebar"] [data-testid="stRadio"] label[data-baseweb="radio"]:hover {
    background: rgba(255,255,255,0.04) !important;
    border-left-color: rgba(63,185,80,0.35);
}

[data-testid="stSidebar"] [data-testid="stRadio"] label[data-baseweb="radio"]:has(input:checked) {
    background: rgba(63,185,80,0.08) !important;
    border-left: 3px solid var(--accent);
}

[data-testid="stSidebar"] [data-testid="stRadio"] label[data-baseweb="radio"] p {
    font-family: 'JetBrains Mono', monospace !important;
    font-size: 0.82rem !important;
    color: #6e7681 !important;
}

[data-testid="stSidebar"] [data-testid="stRadio"] label[data-baseweb="radio"]:has(input:checked) p {
    color: var(--text) !important;
    font-weight: 600 !important;
}

[data-testid="stSidebar"] [data-testid="stRadio"] label[data-baseweb="radio"]:hover p {
    color: #c9d1d9 !important;
}

[data-testid="stSidebar"] [data-testid="stRadio"] label[data-baseweb="radio"] div[data-testid="stMarkdownContainer"] { width: 100%; }

/* Hide radio circles */
[data-testid="stSidebar"] [data-testid="stRadio"] label[data-baseweb="radio"] > div:first-child { display: none !important; }

.block-container { max-width: 1200px; }

.status-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(170px, 1fr));
    gap: 12px;
    margin-bottom: 1.5rem;
}

.status-card {
    background: var(--bg-card);
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 14px 16px;
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.85rem;
}

.status-card .label {
    color: #8b949e;
    font-size: 0.65rem;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    margin-bottom: 6px;
}

.status-card .value { font-weight: 600; font-size: 0.95rem; color: var(--text); }
.status-card .value.ok { color: var(--text); }
.status-card .value.ok-status { color: var(--accent); }
.status-card .value.warn { color: #d29922; }
.status-card .value.err { color: var(--danger); }

.vm-table {
    width: 100%;
    border-collapse: collapse;
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.8rem;
    margin-top: 1rem;
}

.vm-table th {
    text-align: left;
    padding: 10px 12px;
    color: var(--text-muted);
    border-bottom: 1px solid var(--border);
    font-weight: 600;
    text-transform: uppercase;
    font-size: 0.7rem;
    letter-spacing: 0.08em;
}

.vm-table td {
    padding: 8px 12px;
    border-bottom: 1px solid rgba(255,255,255,0.04);
    color: #c9d1d9;
}

.vm-table tr:hover td { background: var(--bg-card); }

.tier-badge {
    display: inline-block;
    padding: 2px 8px;
    border-radius: 4px;
    font-size: 0.7rem;
    font-weight: 600;
}

.tier-0 { background: rgba(63,185,80,0.12); color: var(--accent); }
.tier-1 { background: rgba(56,173,255,0.15); color: #38adff; }
.tier-2 { background: rgba(187,128,255,0.15); color: #bb80ff; }
.clone-linked { color: #38adff; }
.clone-full { color: #8b949e; }

.section-header {
    font-family: 'JetBrains Mono', monospace;
    color: var(--text-muted);
    font-size: 0.75rem;
    text-transform: uppercase;
    letter-spacing: 0.15em;
    margin: 2rem 0 1rem 0;
    padding-bottom: 8px;
    border-bottom: 1px solid var(--border);
}

.hero {
    font-family: 'JetBrains Mono', monospace;
    font-size: 1.6rem;
    font-weight: 700;
    color: var(--text);
    margin-bottom: 0.2rem;
}

.hero .accent { color: var(--accent); }

.hero-sub {
    font-family: 'Inter', sans-serif;
    color: #8b949e;
    font-size: 0.9rem;
    margin-bottom: 2rem;
}

.pb-card-inner {
    display: flex;
    align-items: center;
    gap: 14px;
    padding: 12px 18px;
    box-sizing: border-box;
}

.stApp div[data-testid="stVerticalBlockBorderWrapper"]:has(.pb-card-inner) {
    margin-bottom: 10px !important;
    padding: 0 !important;
    overflow: hidden;
    border-radius: 8px !important;
}

.stApp div[data-testid="stVerticalBlockBorderWrapper"]:has(.pb-card-inner) > div[data-testid="stVerticalBlock"] {
    gap: 0 !important;
    padding: 0 !important;
}

.stApp div[data-testid="stVerticalBlockBorderWrapper"]:has(.pb-card-inner) [data-testid="stHorizontalBlock"] {
    gap: 0 !important;
    align-items: stretch !important;
}

.stApp div[data-testid="stVerticalBlockBorderWrapper"]:has(.pb-card-inner) [data-testid="stHorizontalBlock"] > div[data-testid="column"] {
    padding: 0 !important;
    align-self: stretch !important;
}

.stApp div[data-testid="stVerticalBlockBorderWrapper"]:has(.pb-card-inner) [data-testid="stHorizontalBlock"] > div[data-testid="column"] > div[data-testid="stVerticalBlock"] {
    height: 100% !important;
    justify-content: center !important;
    padding: 0 !important;
    gap: 0 !important;
}

.stApp div[data-testid="stVerticalBlockBorderWrapper"]:has(.pb-card-inner) [data-testid="stHorizontalBlock"] > div[data-testid="column"]:first-child [data-testid="stElementContainer"],
.stApp div[data-testid="stVerticalBlockBorderWrapper"]:has(.pb-card-inner) [data-testid="stHorizontalBlock"] > div[data-testid="column"]:first-child [data-testid="stMarkdownContainer"] {
    margin: 0 !important;
    padding: 0 !important;
    display: flex !important;
    align-items: center !important;
}

.stApp div[data-testid="stVerticalBlockBorderWrapper"]:has(.pb-card-inner) [data-testid="stHorizontalBlock"] > div[data-testid="column"]:last-child {
    flex: 0 0 72px !important;
    width: 72px !important;
    min-width: 72px !important;
    max-width: 72px !important;
    border-left: 1px solid var(--border) !important;
}

.stApp div[data-testid="stVerticalBlockBorderWrapper"]:has(.pb-card-inner) [data-testid="stHorizontalBlock"] > div[data-testid="column"]:last-child > div[data-testid="stVerticalBlock"] {
    display: flex !important;
    flex-direction: column !important;
    justify-content: center !important;
}

.stApp div[data-testid="stVerticalBlockBorderWrapper"]:has(.pb-card-inner) [data-testid="stHorizontalBlock"] > div[data-testid="column"]:last-child [data-testid="stElementContainer"],
.stApp div[data-testid="stVerticalBlockBorderWrapper"]:has(.pb-card-inner) [data-testid="stHorizontalBlock"] > div[data-testid="column"]:last-child div[data-testid="stButton"] {
    margin: 0 !important;
    padding: 0 !important;
    width: 100% !important;
}

.stApp div[data-testid="stVerticalBlockBorderWrapper"]:has(.pb-card-inner) [data-testid="stHorizontalBlock"] > div[data-testid="column"]:last-child div[data-testid="stButton"] > button {
    height: auto !important;
    min-height: 2rem !important;
    width: 100% !important;
    margin: 0 !important;
    padding: 8px 10px !important;
    border: none !important;
    border-radius: 0 !important;
    background: var(--bg-elevated) !important;
    font-size: 0.72rem !important;
    display: inline-flex !important;
    align-items: center !important;
    justify-content: center !important;
    box-sizing: border-box !important;
}

.stApp div[data-testid="stVerticalBlockBorderWrapper"]:has(.pb-card-inner):hover {
    border-color: rgba(63, 185, 80, 0.35) !important;
}

.stApp div[data-testid="stVerticalBlockBorderWrapper"]:has(.pb-card-inner) [data-testid="stHorizontalBlock"] > div[data-testid="column"]:last-child div[data-testid="stButton"] > button:hover {
    background: rgba(255, 255, 255, 0.06) !important;
}

.pb-dot {
    width: 10px;
    height: 10px;
    border-radius: 50%;
    flex-shrink: 0;
}

.pb-info { flex: 1; }

.pb-name {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.85rem;
    font-weight: 500;
    color: #e6edf3;
}

.pb-file {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.65rem;
    color: #484f58;
    margin-top: 2px;
}

.pb-idx {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.65rem;
    color: #30363d;
    min-width: 20px;
}

.metric-big {
    font-family: 'JetBrains Mono', monospace;
    font-size: 2.5rem;
    font-weight: 700;
    color: var(--text);
    line-height: 1;
}

.metric-label {
    font-family: 'Inter', sans-serif;
    font-size: 0.75rem;
    color: #484f58;
    text-transform: uppercase;
    letter-spacing: 0.1em;
}

.deploy-action-label {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.65rem;
    color: var(--text-muted);
    text-transform: uppercase;
    letter-spacing: 0.12em;
    margin-bottom: 6px;
    min-height: 1em;
}

.deploy-action-label.danger {
    color: var(--danger);
}

div[data-testid="stHorizontalBlock"]:has(> div[data-testid="column"]:nth-child(4):last-child) > div[data-testid="column"] {
    flex: 1 1 0 !important;
    min-width: 0 !important;
    align-self: stretch !important;
}

div[data-testid="stHorizontalBlock"]:has(> div[data-testid="column"]:nth-child(4):last-child) div[data-testid="stVerticalBlock"] {
    justify-content: flex-end !important;
}

div[data-testid="stHorizontalBlock"]:has(> div[data-testid="column"]:nth-child(4):last-child) div[data-testid="stButton"] {
    width: 100% !important;
}

div[data-testid="stHorizontalBlock"]:has(> div[data-testid="column"]:nth-child(4):last-child) div[data-testid="stButton"] > button {
    width: 100% !important;
    min-height: 2.5rem !important;
    height: 2.5rem !important;
    padding: 0 1rem !important;
    box-sizing: border-box !important;
    display: inline-flex !important;
    align-items: center !important;
    justify-content: center !important;
}

div[data-testid="stForm"] {
    border: 1px solid var(--border) !important;
    border-radius: 8px !important;
    padding: 24px !important;
    background: var(--bg-card) !important;
}

/* Unified buttons */
.stApp div[data-testid="stButton"] > button,
.stApp div[data-testid="stFormSubmitButton"] > button,
.stApp div.stButton > button {
    font-family: 'JetBrains Mono', monospace !important;
    font-size: 0.78rem !important;
    font-weight: 500 !important;
    padding: 0.5rem 1rem !important;
    border-radius: 6px !important;
    line-height: 1.3 !important;
    min-height: 2.25rem !important;
    transition: all 0.15s ease !important;
}

.stApp div[data-testid="stButton"] > button[kind="secondary"],
.stApp div[data-testid="stFormSubmitButton"] > button[kind="secondaryFormSubmit"],
.stApp div.stButton > button[kind="secondary"] {
    background: var(--bg-elevated) !important;
    border: 1px solid var(--border) !important;
    color: var(--text) !important;
}

.stApp div[data-testid="stButton"] > button[kind="secondary"]:hover,
.stApp div[data-testid="stFormSubmitButton"] > button[kind="secondaryFormSubmit"]:hover,
.stApp div.stButton > button[kind="secondary"]:hover {
    background: rgba(255,255,255,0.06) !important;
    border-color: rgba(63,185,80,0.35) !important;
    color: var(--text) !important;
}

.stApp div[data-testid="stButton"] > button[kind="primary"],
.stApp div.stButton > button[kind="primary"] {
    background: var(--accent) !important;
    color: #ffffff !important;
    border: 1px solid var(--accent) !important;
    font-weight: 600 !important;
}

.stApp div[data-testid="stButton"] > button[kind="primary"]:hover,
.stApp div.stButton > button[kind="primary"]:hover {
    background: var(--accent-dim) !important;
    border-color: var(--accent-dim) !important;
}

.stApp .st-key-deploy_destroy div[data-testid="stButton"] > button {
    background: #da3633 !important;
    border: 1px solid #da3633 !important;
    color: #ffffff !important;
    font-weight: 600 !important;
}

.stApp .st-key-deploy_destroy div[data-testid="stButton"] > button:hover:not(:disabled) {
    background: #b62324 !important;
    border-color: #b62324 !important;
    color: #ffffff !important;
}

.stApp .st-key-deploy_destroy div[data-testid="stButton"] > button:disabled {
    background: rgba(218, 54, 51, 0.35) !important;
    border-color: rgba(218, 54, 51, 0.35) !important;
    color: rgba(255, 255, 255, 0.6) !important;
}

.term-window {
    border: 1px solid #30363d;
    border-radius: 10px;
    overflow: hidden;
    box-shadow: 0 12px 32px rgba(0, 0, 0, 0.35);
    background: #0d1117;
    font-family: 'JetBrains Mono', monospace;
}

.term-window.term-in-card {
    margin: 0;
}

.pb-term-wrap {
    padding: 12px 12px 16px 12px;
    box-sizing: border-box;
}

.stApp div[data-testid="stVerticalBlockBorderWrapper"]:has(.pb-card-inner):has(.pb-term-wrap) {
    overflow: visible !important;
}

.stApp div[data-testid="stVerticalBlockBorderWrapper"]:has(.pb-card-inner):has(.pb-term-wrap) > div[data-testid="stVerticalBlock"] {
    padding-bottom: 4px !important;
}

.term-titlebar {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 9px 14px;
    background: linear-gradient(180deg, #161b22 0%, #0d1117 100%);
    border-bottom: 1px solid #21262d;
}

.term-dots { display: flex; gap: 7px; flex-shrink: 0; }

.term-dot {
    width: 10px;
    height: 10px;
    border-radius: 50%;
}

.term-dot.red { background: #ff5f57; }
.term-dot.yellow { background: #febc2e; }
.term-dot.green { background: #28c840; }

.term-title {
    flex: 1;
    text-align: center;
    font-size: 0.68rem;
    color: #8b949e;
    letter-spacing: 0.04em;
}

.term-status-dot {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    background: #484f58;
    flex-shrink: 0;
}

.term-window.term-running .term-status-dot {
    background: #d29922;
    box-shadow: 0 0 8px rgba(210, 153, 34, 0.6);
    animation: term-pulse 1.2s ease-in-out infinite;
}

.term-window.term-success .term-status-dot {
    background: #3fb950;
    box-shadow: 0 0 8px rgba(63, 185, 80, 0.5);
}

.term-window.term-error .term-status-dot {
    background: #f85149;
    box-shadow: 0 0 8px rgba(248, 81, 73, 0.5);
}

.term-body {
    height: 300px;
    overflow: auto;
    overflow-anchor: none;
    padding: 14px 16px;
    background-color: #010409;
    background-image:
        linear-gradient(rgba(88, 166, 255, 0.03) 1px, transparent 1px),
        linear-gradient(90deg, rgba(88, 166, 255, 0.03) 1px, transparent 1px);
    background-size: 20px 20px;
}

.term-scroll-anchor {
    height: 1px;
    overflow-anchor: auto;
}

.term-body::-webkit-scrollbar { width: 8px; }
.term-body::-webkit-scrollbar-track { background: transparent; }
.term-body::-webkit-scrollbar-thumb {
    background: #30363d;
    border-radius: 4px;
}
.term-body::-webkit-scrollbar-thumb:hover { background: #484f58; }

.term-content {
    font-family: inherit;
    font-size: 0.72rem;
    line-height: 1.5;
    color: #c9d1d9;
}

.term-line {
    display: block;
    white-space: pre;
    min-height: 1.1em;
}

.term-footer {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 7px 14px;
    font-size: 0.67rem;
    border-top: 1px solid #21262d;
    background: #0d1117;
    color: #484f58;
    min-height: 30px;
}

.term-window.term-running .term-footer { color: #d29922; }
.term-window.term-success .term-footer { color: #3fb950; }
.term-window.term-error .term-footer { color: #f85149; }

.t-prompt { color: #3fb950; font-weight: 600; }
.t-comment { color: #58a6ff; }
.t-add { color: #7ee787; }
.t-del { color: #ff7b72; }
.t-change { color: #ffa657; }
.t-error { color: #ff7b72; font-weight: 600; }
.t-action { color: #e6edf3; font-weight: 600; }
.t-info { color: #8b949e; }
.t-key { color: #79c0ff; }
.t-val { color: #a5d6ff; }
.t-str { color: #a5d6ff; }
.t-num { color: #ffa657; }
.t-idle-hint { color: #484f58; }
.t-cursor {
    color: #3fb950;
    animation: term-blink 1s step-end infinite;
}

@keyframes term-pulse {
    0%, 100% { opacity: 1; transform: scale(1); }
    50% { opacity: 0.5; transform: scale(0.85); }
}

@keyframes term-blink {
    0%, 100% { opacity: 1; }
    50% { opacity: 0; }
}

code { font-family: 'JetBrains Mono', monospace !important; }
</style>
"""

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def file_exists(path: str) -> bool:
    return os.path.exists(path)


def subprocess_env() -> dict[str, str]:
    env = os.environ.copy()
    if sys.platform == "darwin":
        env.setdefault("OBJC_DISABLE_INITIALIZE_FORK_SAFETY", "YES")
    return env


def ensure_cyberlab_dir():
    os.makedirs(CYBERLAB_DIR, exist_ok=True)


def process_running(pid: int | None) -> bool:
    if not pid:
        return False
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def read_deploy_status() -> dict:
    if not file_exists(DEPLOY_STATUS_FILE):
        return {"state": "idle", "footer": "ready"}
    try:
        with open(DEPLOY_STATUS_FILE) as f:
            return json.load(f)
    except Exception:
        return {"state": "idle", "footer": "ready"}


def write_deploy_status(
    state: str,
    footer: str,
    *,
    pid: int | None = None,
    cmd: str | None = None,
    ok_msg: str = "",
    err_msg: str = "",
):
    ensure_cyberlab_dir()
    payload = {
        "state": state,
        "footer": footer,
        "pid": pid,
        "cmd": cmd,
        "ok_msg": ok_msg,
        "err_msg": err_msg,
    }
    with open(DEPLOY_STATUS_FILE, "w") as f:
        json.dump(payload, f)


def read_deploy_log() -> str:
    if not file_exists(DEPLOY_LOG):
        return ""
    with open(DEPLOY_LOG) as f:
        return f.read()


def count_deployed_vms(state_file: str) -> int:
    if not file_exists(state_file):
        return 0
    try:
        with open(state_file) as f:
            state = json.load(f)
        return sum(
            len(r.get("instances", []))
            for r in state.get("resources", [])
            if r.get("type") == "proxmox_vm_qemu"
        )
    except Exception:
        return 0


def is_deploy_job_running() -> bool:
    status = read_deploy_status()
    if status.get("state") != "running":
        return False
    return process_running(status.get("pid"))


def poll_deploy_job() -> dict:
    """Reconcile background deploy job; update status file when process exits."""
    status = read_deploy_status()
    if status.get("state") != "running":
        return status

    pid = status.get("pid")
    if process_running(pid):
        return status

    rc = 1
    if file_exists(DEPLOY_EXIT_FILE):
        try:
            rc = int(open(DEPLOY_EXIT_FILE).read().strip())
        except Exception:
            rc = 1

    ok_msg = status.get("ok_msg") or "complete"
    err_msg = status.get("err_msg") or "failed"
    if rc == 0:
        write_deploy_status("success", ok_msg, cmd=status.get("cmd"), ok_msg=ok_msg, err_msg=err_msg)
    else:
        write_deploy_status("error", err_msg, cmd=status.get("cmd"), ok_msg=ok_msg, err_msg=err_msg)
    return read_deploy_status()


def sync_deploy_from_disk():
    status = poll_deploy_job()
    st.session_state.deploy_output = read_deploy_log()
    st.session_state.deploy_status = (status.get("state", "idle"), status.get("footer", "ready"))


def start_deploy_job(cmd: str, cwd: str, ok_msg: str, err_msg: str) -> bool:
    if is_deploy_job_running() or is_any_playbook_job_running():
        return False

    ensure_cyberlab_dir()
    with open(DEPLOY_LOG, "w") as f:
        f.write(f"$ {cmd}\n\n")
    if file_exists(DEPLOY_EXIT_FILE):
        os.remove(DEPLOY_EXIT_FILE)

    wrapper = f'({cmd}) >> "{DEPLOY_LOG}" 2>&1; echo $? > "{DEPLOY_EXIT_FILE}"'
    popen_kwargs: dict = {
        "shell": True,
        "cwd": cwd,
        "env": subprocess_env(),
        "start_new_session": True,
    }
    proc = subprocess.Popen(wrapper, **popen_kwargs)
    write_deploy_status(
        "running",
        f"running: {cmd.split()[0]}…",
        pid=proc.pid,
        cmd=cmd,
        ok_msg=ok_msg,
        err_msg=err_msg,
    )
    st.session_state.deploy_output = read_deploy_log()
    st.session_state.deploy_status = ("running", f"running: {cmd.split()[0]}…")
    return True


def playbook_job_key(pb_file: str) -> str:
    return pb_file.replace("/", "_")


def playbook_job_paths(key: str) -> dict[str, str]:
    job_dir = os.path.join(PLAYBOOKS_JOB_DIR, key)
    return {
        "dir": job_dir,
        "log": os.path.join(job_dir, "run.log"),
        "status": os.path.join(job_dir, "status.json"),
        "exit": os.path.join(job_dir, "exit"),
    }


def read_playbook_status(key: str) -> dict:
    paths = playbook_job_paths(key)
    if not file_exists(paths["status"]):
        return {"state": "idle", "footer": "ready"}
    try:
        with open(paths["status"]) as f:
            return json.load(f)
    except Exception:
        return {"state": "idle", "footer": "ready"}


def write_playbook_status(
    key: str,
    state: str,
    footer: str,
    *,
    pid: int | None = None,
    cmd: str | None = None,
    ok_msg: str = "",
    err_msg: str = "",
    pb_file: str | None = None,
):
    paths = playbook_job_paths(key)
    os.makedirs(paths["dir"], exist_ok=True)
    payload = {
        "state": state,
        "footer": footer,
        "pid": pid,
        "cmd": cmd,
        "ok_msg": ok_msg,
        "err_msg": err_msg,
        "pb_file": pb_file,
    }
    with open(paths["status"], "w") as f:
        json.dump(payload, f)


def read_playbook_log(key: str) -> str:
    paths = playbook_job_paths(key)
    if not file_exists(paths["log"]):
        return ""
    with open(paths["log"]) as f:
        return f.read()


def is_playbook_job_running(key: str) -> bool:
    status = read_playbook_status(key)
    if status.get("state") != "running":
        return False
    return process_running(status.get("pid"))


def is_any_playbook_job_running() -> bool:
    if is_playbook_job_running(BATCH_PLAYBOOK_KEY):
        return True
    return any(is_playbook_job_running(playbook_job_key(pb_file)) for pb_file, _, _ in PLAYBOOKS)


def poll_playbook_job(key: str) -> dict:
    status = read_playbook_status(key)
    if status.get("state") != "running":
        return status

    pid = status.get("pid")
    if process_running(pid):
        return status

    paths = playbook_job_paths(key)
    rc = 1
    if file_exists(paths["exit"]):
        try:
            rc = int(open(paths["exit"]).read().strip())
        except Exception:
            rc = 1

    ok_msg = status.get("ok_msg") or "complete"
    err_msg = status.get("err_msg") or "failed"
    if rc == 0:
        write_playbook_status(
            key, "success", ok_msg,
            cmd=status.get("cmd"), ok_msg=ok_msg, err_msg=err_msg, pb_file=status.get("pb_file"),
        )
    else:
        write_playbook_status(
            key, "error", err_msg,
            cmd=status.get("cmd"), ok_msg=ok_msg, err_msg=err_msg, pb_file=status.get("pb_file"),
        )
    return read_playbook_status(key)


def sync_playbook_from_disk(pb_file: str):
    key = playbook_job_key(pb_file)
    poll_playbook_job(key)
    paths = playbook_job_paths(key)
    if file_exists(paths["log"]) or file_exists(paths["status"]):
        st.session_state.playbook_outputs[pb_file] = read_playbook_log(key)
        status = read_playbook_status(key)
        st.session_state.playbook_status[pb_file] = (
            status.get("state", "idle"), status.get("footer", "ready")
        )


def sync_all_playbooks_from_disk():
    for pb_file, _, _ in PLAYBOOKS:
        sync_playbook_from_disk(pb_file)


def playbook_has_output(pb_file: str) -> bool:
    key = playbook_job_key(pb_file)
    paths = playbook_job_paths(key)
    return file_exists(paths["log"]) or pb_file in st.session_state.get("playbook_outputs", {})


def start_playbook_job(
    key: str,
    cmd: str,
    cwd: str,
    ok_msg: str,
    err_msg: str,
    *,
    pb_file: str | None = None,
    running_label: str | None = None,
) -> bool:
    if is_playbook_job_running(key):
        return False

    paths = playbook_job_paths(key)
    os.makedirs(paths["dir"], exist_ok=True)
    with open(paths["log"], "w") as f:
        f.write(f"$ {cmd}\n\n")
    if file_exists(paths["exit"]):
        os.remove(paths["exit"])

    wrapper = f'({cmd}) >> "{paths["log"]}" 2>&1; echo $? > "{paths["exit"]}"'
    proc = subprocess.Popen(
        wrapper, shell=True, cwd=cwd, env=subprocess_env(), start_new_session=True,
    )
    label = running_label or pb_file or key
    write_playbook_status(
        key,
        "running",
        f"running: {label}…",
        pid=proc.pid,
        cmd=cmd,
        ok_msg=ok_msg,
        err_msg=err_msg,
        pb_file=pb_file,
    )
    if pb_file:
        st.session_state.playbook_outputs[pb_file] = read_playbook_log(key)
        st.session_state.playbook_status[pb_file] = ("running", f"running: {label}…")
    return True


def run_clean_known_hosts(placeholder):
    if not file_exists(CLEAN_HOSTS_SCRIPT):
        return 1, f"Script not found: {CLEAN_HOSTS_SCRIPT}"
    os.chmod(CLEAN_HOSTS_SCRIPT, 0o755)
    return run_command(f'"{CLEAN_HOSTS_SCRIPT}"', BASE_DIR, placeholder)


def check_tool(name: str) -> str | None:
    return shutil.which(name)


def highlight_terminal_output(text: str) -> str:
    raw_lines = text.split("\n")
    lines = []
    for i, line in enumerate(raw_lines):
        if i == 0 and line.startswith("$ "):
            cmd = html.escape(line[2:])
            content = f'<span class="t-prompt">$</span> {cmd}'
        elif not line and i > 0:
            content = "&nbsp;"
        else:
            stripped = line.strip()
            if stripped.startswith("# "):
                content = f'<span class="t-comment">{html.escape(line)}</span>'
            elif stripped.startswith("+") or " + create" in line:
                content = f'<span class="t-add">{html.escape(line)}</span>'
            elif stripped.startswith("-") or " - destroy" in line:
                content = f'<span class="t-del">{html.escape(line)}</span>'
            elif stripped.startswith("~") or " ~ update" in line:
                content = f'<span class="t-change">{html.escape(line)}</span>'
            elif "Error:" in line or "error:" in line.lower():
                content = f'<span class="t-error">{html.escape(line)}</span>'
            elif "will be created" in line or "will be destroyed" in line or "will be updated" in line:
                content = f'<span class="t-action">{html.escape(line)}</span>'
            elif stripped.startswith("Plan:") or "No changes." in line or "Apply complete!" in line:
                content = f'<span class="t-info">{html.escape(line)}</span>'
            elif m := re.match(r"^(\s+)(\w+)\s*=\s*(.+)$", line):
                indent, key, val = m.groups()
                val_html = html.escape(val)
                if val.startswith('"') or val.startswith("'"):
                    val_html = f'<span class="t-str">{val_html}</span>'
                elif val in ("true", "false"):
                    val_html = f'<span class="t-info">{val_html}</span>'
                elif re.fullmatch(r"-?\d+", val):
                    val_html = f'<span class="t-num">{val_html}</span>'
                content = (
                    f'{html.escape(indent)}<span class="t-key">{html.escape(key)}</span> = {val_html}'
                )
            else:
                content = html.escape(line)
        lines.append(f'<div class="term-line">{content}</div>')
    return "".join(lines)


def inject_terminal_autoscroll():
    components.html(
        """<script>
(function () {
  const doc = window.parent.document;
  if (doc.__cyberlabTermScrollInit) return;
  doc.__cyberlabTermScrollInit = true;
  doc.__cyberlabTermPinState = doc.__cyberlabTermPinState || {};

  function nearBottom(el) {
    return el.scrollHeight - el.scrollTop - el.clientHeight < 48;
  }

  function scrollToBottom(el) {
    requestAnimationFrame(() => {
      el.scrollTop = el.scrollHeight;
    });
  }

  function termId(el) {
    return el.dataset.termId || "default";
  }

  function isPinned(el) {
    const id = termId(el);
    return doc.__cyberlabTermPinState[id] !== false;
  }

  function syncTerminals() {
    doc.querySelectorAll(".term-body[data-term-autoscroll]").forEach((el) => {
      if (isPinned(el)) {
        scrollToBottom(el);
      }
    });
  }

  doc.addEventListener(
    "scroll",
    (e) => {
      const el = e.target;
      if (!el.classList || !el.classList.contains("term-body")) return;
      doc.__cyberlabTermPinState[termId(el)] = nearBottom(el);
    },
    true
  );

  const obs = new MutationObserver(() => syncTerminals());
  obs.observe(doc.body, { childList: true, subtree: true, characterData: true });
  syncTerminals();
})();
</script>""",
        height=0,
        width=0,
    )


def render_terminal(
    placeholder,
    text: str = "",
    state: str = "idle",
    footer: str = "ready",
    title: str = "cyberlab@deploy — zsh",
    extra_class: str = "",
    term_id: str | None = None,
):
    if not text:
        body = (
            '<div class="term-line">'
            '<span class="t-prompt">$</span> '
            '<span class="t-cursor">▋</span> '
            '<span class="t-idle-hint">waiting for command…</span>'
            '</div>'
        )
    else:
        body = highlight_terminal_output(text)

    footer_text = html.escape(footer) if footer else "ready"
    footer_prefix = {"running": "▶", "success": "✓", "error": "✕", "idle": "○"}.get(state, "○")
    window_class = f"term-window term-{state} {extra_class}".strip()
    tid = html.escape(term_id or title)

    terminal_html = f'''<div class="{window_class}">
<div class="term-titlebar">
  <div class="term-dots">
    <span class="term-dot red"></span>
    <span class="term-dot yellow"></span>
    <span class="term-dot green"></span>
  </div>
  <div class="term-title">{html.escape(title)}</div>
  <div class="term-status-dot"></div>
</div>
<div class="term-body" data-term-autoscroll="true" data-term-id="{tid}"><div class="term-content">{body}</div><div class="term-scroll-anchor"></div></div>
<div class="term-footer">{footer_prefix} {footer_text}</div>
</div>'''

    if "term-in-card" in extra_class:
        terminal_html = f'<div class="pb-term-wrap">{terminal_html}</div>'

    placeholder.markdown(terminal_html, unsafe_allow_html=True)


def render_deploy_terminal(placeholder, text: str = "", state: str | None = None, footer: str | None = None):
    session_state, session_footer = st.session_state.get("deploy_status", ("idle", "ready"))
    render_terminal(
        placeholder,
        text,
        state=session_state if state is None else state,
        footer=session_footer if footer is None else footer,
        term_id="deploy",
    )


def run_command(cmd: str, cwd: str, placeholder, save_output=None, render=None, render_interval: float = 0.15):
    render_fn = render or (lambda ph, t: ph.code(t, language="bash"))
    output_lines = [f"$ {cmd}\n\n"]
    text = "".join(output_lines)
    render_fn(placeholder, text)
    if save_output:
        save_output(text)

    popen_kwargs: dict = {
        "shell": True,
        "cwd": cwd,
        "env": subprocess_env(),
        "stdout": subprocess.PIPE,
        "stderr": subprocess.STDOUT,
        "text": True,
        "bufsize": 1,
    }
    if sys.platform == "darwin":
        popen_kwargs["start_new_session"] = True

    proc = subprocess.Popen(cmd, **popen_kwargs)
    last_render = time.monotonic()
    try:
        for line in proc.stdout:
            if line and not line.endswith("\n"):
                line += "\n"
            output_lines.append(line)
            text = "".join(output_lines)
            if save_output:
                save_output(text)
            now = time.monotonic()
            if now - last_render >= render_interval:
                render_fn(placeholder, text)
                last_render = now
    finally:
        proc.wait()

    text = "".join(output_lines)
    render_fn(placeholder, text)
    if save_output:
        save_output(text)
    return proc.returncode, text


def hero(title: str) -> str:
    return f'<div class="hero"><span class="accent">//</span> {title}</div>'


def status_card(label: str, value: str, state: str = "ok") -> str:
    return f'<div class="status-card"><div class="label">{label}</div><div class="value {state}">{value}</div></div>'


def section(title: str):
    st.markdown(f'<div class="section-header">{title}</div>', unsafe_allow_html=True)


def pb_card_html(idx: int, name: str, filename: str, color: str) -> str:
    return f'''<div class="pb-card-inner">
        <div class="pb-idx">{idx:02d}</div>
        <div class="pb-dot" style="background:{color};"></div>
        <div class="pb-info">
            <div class="pb-name">{name}</div>
            <div class="pb-file">playbooks/{filename}</div>
        </div>
    </div>'''


# ---------------------------------------------------------------------------
# Pages
# ---------------------------------------------------------------------------

def page_dashboard():
    st.markdown(hero("Dashboard"), unsafe_allow_html=True)
    st.markdown('<div class="hero-sub">CyberLab environment overview</div>', unsafe_allow_html=True)

    tools = {"terraform": check_tool("terraform"), "ansible": check_tool("ansible"), "ansible-playbook": check_tool("ansible-playbook")}
    files_check = {
        "terraform.tfvars": os.path.join(TERRAFORM_DIR, "terraform.tfvars"),
        "vms.json": os.path.join(TERRAFORM_DIR, "vms.json"),
        ".vault_pass": os.path.join(ANSIBLE_DIR, ".vault_pass"),
        "secret_vault.yml": os.path.join(ANSIBLE_DIR, "inventory", "group_vars", "secret_vault.yml"),
    }

    cards = '<div class="status-grid">'
    for t, path in tools.items():
        cards += status_card(t, "ready" if path else "missing", "ok-status" if path else "err")
    for name, path in files_check.items():
        cards += status_card(name, "found" if file_exists(path) else "missing", "ok-status" if file_exists(path) else "warn")
    tf_init = file_exists(os.path.join(TERRAFORM_DIR, ".terraform"))
    cards += status_card("tf init", "yes" if tf_init else "no", "ok-status" if tf_init else "warn")
    cards += '</div>'
    st.markdown(cards, unsafe_allow_html=True)

    vm_count = count_deployed_vms(os.path.join(TERRAFORM_DIR, "terraform.tfstate"))

    vms_path = os.path.join(TERRAFORM_DIR, "vms.json")
    vms = []
    if file_exists(vms_path):
        with open(vms_path) as f:
            data = json.load(f)
        vms = data.get("vms", [])

    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown(f'<div class="metric-big">{len(vms)}</div><div class="metric-label">VMs Defined</div>', unsafe_allow_html=True)
    with col2:
        st.markdown(f'<div class="metric-big">{vm_count}</div><div class="metric-label">VMs Deployed</div>', unsafe_allow_html=True)
    with col3:
        total_ram = sum(v.get("memory", 0) for v in vms)
        st.markdown(f'<div class="metric-big">{total_ram // 1024}G</div><div class="metric-label">Total RAM</div>', unsafe_allow_html=True)

    if vms:
        section("lab topology")
        rows = ""
        for vm in vms:
            deps = vm.get("depends_on", [])
            tn = 0 if not deps else (1 if len(deps) == 1 else 2)
            ct = "linked" if not vm.get("full_clone", True) else "full"
            disk = next((d.get("size", "") for d in vm.get("disks", []) if d.get("type") == "disk"), "")
            ip = ""
            ci = vm.get("cloudinit", {})
            if ci.get("enabled") and ci.get("ipconfig"):
                ip = ci["ipconfig"][0].get("ip", "")
            rows += f'<tr><td><span class="tier-badge tier-{tn}">T{tn}</span></td><td><strong>{vm["name"]}</strong></td><td>{vm["vmid"]}</td><td>{vm.get("clone","")}</td><td>{vm.get("cpu",{}).get("cores","")}c / {vm.get("memory","")}M</td><td>{disk}</td><td class="clone-{ct}">{ct}</td><td><code>{ip}</code></td></tr>'
        st.markdown(f'<table class="vm-table"><thead><tr><th>Tier</th><th>Name</th><th>VMID</th><th>Template</th><th>CPU/RAM</th><th>Disk</th><th>Clone</th><th>IP</th></tr></thead><tbody>{rows}</tbody></table>', unsafe_allow_html=True)


def page_terraform_config():
    st.markdown(hero("Terraform Config"), unsafe_allow_html=True)
    st.markdown('<div class="hero-sub">Proxmox API credentials & template passwords</div>', unsafe_allow_html=True)

    tf_vars_path = os.path.join(TERRAFORM_DIR, "terraform.tfvars")
    existing = {}
    existing_passwords = {}
    if file_exists(tf_vars_path):
        st.markdown(f'<div class="status-grid">{status_card("terraform.tfvars", "found", "ok-status")}</div>', unsafe_allow_html=True)
        try:
            with open(tf_vars_path) as f:
                content = f.read()
            in_passwords = False
            for line in content.splitlines():
                stripped = line.strip()
                if stripped.startswith("#") or not stripped:
                    continue
                if stripped.startswith("template_passwords"):
                    in_passwords = True
                    continue
                if stripped == "}":
                    in_passwords = False
                    continue
                if "=" in stripped:
                    k, v = stripped.split("=", 1)
                    k = k.strip().strip('"')
                    v = v.strip().strip('"')
                    if in_passwords and k in TEMPLATES:
                        existing_passwords[k] = v
                    elif not in_passwords and k in ("proxmox_api_url", "proxmox_api_token_id", "proxmox_api_token_secret"):
                        existing[k] = v
        except Exception:
            pass

    if existing:
        section("current config")
        cards = '<div class="status-grid">'
        cards += status_card("api url", existing.get("proxmox_api_url", "—"), "ok")
        cards += status_card("token id", existing.get("proxmox_api_token_id", "—"), "ok")
        secret = existing.get("proxmox_api_token_secret", "")
        cards += status_card("token secret", f"••••••{secret[-6:]}" if secret else "—", "ok")
        cards += '</div>'
        st.markdown(cards, unsafe_allow_html=True)

        if existing_passwords:
            pw_cards = '<div class="status-grid">'
            for tpl, pw in existing_passwords.items():
                masked = f"{pw[:2]}{'•' * (len(pw) - 4)}{pw[-2:]}" if len(pw) > 4 else "••••"
                pw_cards += status_card(tpl, masked, "ok")
            pw_cards += '</div>'
            st.markdown(pw_cards, unsafe_allow_html=True)

    section("proxmox api")
    api_url = st.text_input("API URL", value=existing.get("proxmox_api_url", "https://your-proxmox:8006/api2/json"))
    c1, c2 = st.columns(2)
    with c1:
        token_id = st.text_input("Token ID", value=existing.get("proxmox_api_token_id", "terraform@pam!terraform"))
    with c2:
        token_secret = st.text_input("Token Secret", type="password", value=existing.get("proxmox_api_token_secret", ""))

    section("template passwords")
    all_same = len(set(existing_passwords.values())) <= 1 if existing_passwords else True
    use_same = st.checkbox("Same password for all templates", value=all_same)
    passwords = {}
    if use_same:
        default_pw = next(iter(existing_passwords.values()), "") if existing_passwords else ""
        common = st.text_input("Password for all templates", type="password", value=default_pw)
        for t in TEMPLATES:
            passwords[t] = common
    else:
        cols = st.columns(2)
        for idx, t in enumerate(TEMPLATES):
            with cols[idx % 2]:
                passwords[t] = st.text_input(t, type="password", key=f"pw_{t}", value=existing_passwords.get(t, ""))

    if st.button("Save", type="primary", use_container_width=True):
        if not api_url or not token_id or not token_secret:
            st.error("All Proxmox API fields are required.")
        else:
            content = "# Proxmox API Configuration\n"
            content += f'proxmox_api_url          = "{api_url}"\n'
            content += f'proxmox_api_token_id     = "{token_id}"\n'
            content += f'proxmox_api_token_secret = "{token_secret}"\n'
            content += "\n# Template-based passwords\n"
            content += "template_passwords = {\n"
            for t, pw in passwords.items():
                if pw:
                    content += f'  "{t}" = "{pw}"\n'
            content += "}\n"
            with open(tf_vars_path, "w") as f:
                f.write(content)
            os.chmod(tf_vars_path, 0o600)
            st.success("Saved")
            st.rerun()


def page_vm_editor():
    st.markdown(hero("Virtual Machines"), unsafe_allow_html=True)
    st.markdown('<div class="hero-sub">Edit VM definitions for Terraform provisioning</div>', unsafe_allow_html=True)

    vms_path = os.path.join(TERRAFORM_DIR, "vms.json")
    example_path = os.path.join(TERRAFORM_DIR, "vms.json.example")

    if not file_exists(vms_path):
        st.warning("vms.json not found.")
        if file_exists(example_path) and st.button("Create from example", type="primary"):
            shutil.copy2(example_path, vms_path)
            st.rerun()
        return

    with open(vms_path) as f:
        data = json.load(f)
    vms = data.get("vms", [])

    for i, vm in enumerate(vms):
        deps = vm.get("depends_on", [])
        tn = 0 if not deps else (1 if len(deps) == 1 else 2)
        label = f"`T{tn}` **{vm['name']}** -- {vm.get('clone', '')} -- VMID {vm['vmid']}"
        with st.expander(label, expanded=False):
            col1, col2, col3 = st.columns(3)
            with col1:
                vm["name"] = st.text_input("Name", vm["name"], key=f"name_{i}")
                vm["vmid"] = st.number_input("VMID", value=vm["vmid"], key=f"vmid_{i}")
                vm["clone"] = st.text_input("Template", vm.get("clone", ""), key=f"clone_{i}")
                vm["target_node"] = st.text_input("Node", vm.get("target_node", "proxmox"), key=f"node_{i}")
            with col2:
                cpu = vm.get("cpu", {})
                cpu["cores"] = st.number_input("Cores", value=cpu.get("cores", 1), min_value=1, key=f"cores_{i}")
                cpu["sockets"] = st.number_input("Sockets", value=cpu.get("sockets", 1), min_value=1, key=f"sockets_{i}")
                vm["cpu"] = cpu
                vm["memory"] = st.number_input("RAM (MB)", value=vm.get("memory", 1024), step=512, key=f"mem_{i}")
                vm["balloon"] = st.number_input("Balloon (MB)", value=vm.get("balloon", vm.get("memory", 1024)), step=512, key=f"balloon_{i}")
            with col3:
                vm["full_clone"] = st.selectbox("Clone", [True, False], index=0 if vm.get("full_clone", True) else 1, format_func=lambda x: "Full" if x else "Linked", key=f"fc_{i}")
                vm["onboot"] = st.checkbox("Autostart", value=vm.get("onboot", False), key=f"onboot_{i}")
                for d in vm.get("disks", []):
                    if d.get("type") == "disk":
                        d["size"] = st.text_input("Disk", d.get("size", "32G"), key=f"disk_{i}")
                        break
            ci = vm.get("cloudinit", {})
            if ci.get("enabled"):
                section("cloud-init")
                c1, c2 = st.columns(2)
                with c1:
                    if ci.get("ipconfig"):
                        ci["ipconfig"][0]["ip"] = st.text_input("IP/CIDR", ci["ipconfig"][0].get("ip", ""), key=f"ip_{i}")
                        ci["ipconfig"][0]["gateway"] = st.text_input("Gateway", ci["ipconfig"][0].get("gateway", ""), key=f"gw_{i}")
                with c2:
                    ci["nameserver"] = st.text_input("DNS", ci.get("nameserver", ""), key=f"ns_{i}")
                    ci["searchdomain"] = st.text_input("Domain", ci.get("searchdomain", ""), key=f"sd_{i}")

    if st.button("Save vms.json", type="primary", use_container_width=True):
        data["vms"] = vms
        with open(vms_path, "w") as f:
            json.dump(data, f, indent=4)
        st.success("Saved")


def _decrypt_vault(vault_path: str, vault_pass_path: str) -> dict | None:
    cmd = f'ansible-vault view --vault-password-file "{vault_pass_path}" "{vault_path}"'
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True, cwd=ANSIBLE_DIR, env=subprocess_env())
    if result.returncode != 0:
        return None
    try:
        return yaml.safe_load(result.stdout) or {}
    except Exception:
        return None


def page_ansible_secrets():
    st.markdown(hero("Ansible Vault"), unsafe_allow_html=True)
    st.markdown('<div class="hero-sub">Manage encrypted credentials</div>', unsafe_allow_html=True)

    vault_pass_path = os.path.join(ANSIBLE_DIR, ".vault_pass")
    vault_path = os.path.join(ANSIBLE_DIR, "inventory", "group_vars", "secret_vault.yml")

    tab1, tab2, tab3 = st.tabs(["View Vault", "Edit Vault", "Vault Password"])

    with tab1:
        has_pass = file_exists(vault_pass_path)
        has_vault = file_exists(vault_path)
        cards = '<div class="status-grid">'
        cards += status_card(".vault_pass", "found" if has_pass else "missing", "ok-status" if has_pass else "err")
        cards += status_card("secret_vault.yml", "encrypted" if has_vault else "missing", "ok-status" if has_vault else "warn")
        cards += '</div>'
        st.markdown(cards, unsafe_allow_html=True)

        if not has_pass or not has_vault:
            st.info("Both `.vault_pass` and `secret_vault.yml` are needed to view secrets.")
        else:
            if st.button("Decrypt & View", type="primary"):
                data = _decrypt_vault(vault_path, vault_pass_path)
                if data is None:
                    st.error("Decryption failed. Check your vault password.")
                else:
                    groups = {
                        "Windows / AD": ["win_username", "win_password", "dsrm_password"],
                        "Domain Users": ["dave_password", "sophia_password"],
                        "ELK Stack": ["elastic_custom_password"],
                        "Wazuh": ["wazuh_api_password", "wazuh_admin_password"],
                    }
                    for gname, fields in groups.items():
                        section(gname)
                        h = '<div class="status-grid">'
                        for f in fields:
                            h += status_card(f.replace("_", " "), str(data.get(f, "\u2014")), "ok")
                        h += '</div>'
                        st.markdown(h, unsafe_allow_html=True)
                    extra = {k: v for k, v in data.items() if not any(k in fs for fs in groups.values())}
                    if extra:
                        section("other")
                        h = '<div class="status-grid">'
                        for k, v in extra.items():
                            h += status_card(k.replace("_", " "), str(v), "ok")
                        h += '</div>'
                        st.markdown(h, unsafe_allow_html=True)

    with tab2:
        if not file_exists(vault_pass_path):
            st.info("Create `.vault_pass` first (Vault Password tab).")
            return
        defaults = {}
        if file_exists(vault_path) and file_exists(vault_pass_path):
            defaults = _decrypt_vault(vault_path, vault_pass_path) or {}

        with st.form("vault_form"):
            section("windows / active directory")
            c1, c2 = st.columns(2)
            with c1:
                win_username = st.text_input("Admin Username", value=defaults.get("win_username", "Administrator"))
                win_password = st.text_input("Admin Password", type="password", value=defaults.get("win_password", ""))
            with c2:
                dsrm_password = st.text_input("DSRM Password", type="password", value=defaults.get("dsrm_password", ""))
            section("domain users")
            c1, c2 = st.columns(2)
            with c1:
                dave_password = st.text_input("Dave Password", type="password", value=defaults.get("dave_password", ""))
            with c2:
                sophia_password = st.text_input("Sophia Password", type="password", value=defaults.get("sophia_password", ""))
            section("elk stack")
            elastic_password = st.text_input("Elastic Password", type="password", value=defaults.get("elastic_custom_password", ""))
            section("wazuh")
            c1, c2 = st.columns(2)
            with c1:
                wazuh_api_pw = st.text_input("API Password", type="password", value=defaults.get("wazuh_api_password", ""))
            with c2:
                wazuh_admin_pw = st.text_input("Admin Password", type="password", key="wazuh_adm", value=defaults.get("wazuh_admin_password", ""))

            if st.form_submit_button("Encrypt & Save", type="primary", use_container_width=True):
                vault_content = (
                    f"---\nwin_username: {win_username}\nwin_password: {win_password}\n\n"
                    f"dsrm_password: {dsrm_password}\n\n"
                    f"dave_password: {dave_password}\nsophia_password: {sophia_password}\n\n"
                    f"elastic_custom_password: {elastic_password}\n\n"
                    f"wazuh_api_password: {wazuh_api_pw}\nwazuh_admin_password: {wazuh_admin_pw}\n"
                )
                with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".yml") as tmp:
                    tmp.write(vault_content)
                    tmp_path = tmp.name
                try:
                    cmd = f'ansible-vault encrypt --encrypt-vault-id default --vault-password-file "{vault_pass_path}" "{tmp_path}"'
                    result = subprocess.run(cmd, shell=True, capture_output=True, text=True, cwd=ANSIBLE_DIR, env=subprocess_env())
                    if result.returncode != 0:
                        st.error(f"Encryption failed: {result.stderr}")
                        os.unlink(tmp_path)
                    else:
                        shutil.move(tmp_path, vault_path)
                        os.chmod(vault_path, 0o600)
                        st.success("Encrypted and saved")
                        st.rerun()
                except Exception as e:
                    st.error(f"Error: {e}")
                    if os.path.exists(tmp_path):
                        os.unlink(tmp_path)

    with tab3:
        exists = file_exists(vault_pass_path)
        st.markdown(f'<div class="status-grid">{status_card(".vault_pass", "found" if exists else "missing", "ok-status" if exists else "warn")}</div>', unsafe_allow_html=True)
        with st.form("vault_pass_form"):
            vault_pw = st.text_input("Vault Password", type="password")
            if st.form_submit_button("Save", type="primary", use_container_width=True):
                if not vault_pw:
                    st.error("Password cannot be empty.")
                else:
                    with open(vault_pass_path, "w") as f:
                        f.write(vault_pw + "\n")
                    os.chmod(vault_pass_path, 0o600)
                    st.success("Saved")
                    st.rerun()


def _close_destroy_dialog():
    st.session_state.show_destroy_dialog = False


@st.dialog("Destroy infrastructure?", on_dismiss=_close_destroy_dialog)
def destroy_confirm_dialog():
    st.warning("This will permanently delete all Terraform-managed VMs from Proxmox.")
    st.caption("This action cannot be undone.")
    cancel_col, confirm_col = st.columns(2)
    with cancel_col:
        if st.button("Cancel", use_container_width=True):
            _close_destroy_dialog()
            st.rerun()
    with confirm_col:
        if st.button("Yes, destroy", type="primary", use_container_width=True):
            _close_destroy_dialog()
            st.session_state.run_destroy = True
            st.rerun()


def _deploy_terminal_fragment():
    status = poll_deploy_job()
    text = read_deploy_log()
    state = status.get("state", "idle")
    footer = status.get("footer", "ready")
    st.session_state.deploy_output = text
    st.session_state.deploy_status = (state, footer)
    render_deploy_terminal(st.empty(), text, state=state, footer=footer)


def page_deploy():
    st.markdown(hero("Deploy"), unsafe_allow_html=True)
    st.markdown('<div class="hero-sub">Provision infrastructure on Proxmox</div>', unsafe_allow_html=True)

    if "deploy_output" not in st.session_state:
        st.session_state.deploy_output = ""
    if "deploy_status" not in st.session_state:
        st.session_state.deploy_status = ("idle", "ready")
    if "show_destroy_dialog" not in st.session_state:
        st.session_state.show_destroy_dialog = False

    sync_deploy_from_disk()

    vms_path = os.path.join(TERRAFORM_DIR, "vms.json")
    if not file_exists(vms_path):
        st.error("vms.json missing. Configure VMs first.")
        return

    tf_init = file_exists(os.path.join(TERRAFORM_DIR, ".terraform"))
    run_destroy = st.session_state.get("run_destroy", False)
    job_running = is_deploy_job_running() or is_any_playbook_job_running()

    section("terraform actions")
    tf_cols = st.columns(4, gap="small")
    with tf_cols[0]:
        init_btn = st.button("Initialize", use_container_width=True, disabled=job_running)
    with tf_cols[1]:
        plan_btn = st.button("Plan", use_container_width=True, disabled=not tf_init or job_running)
    with tf_cols[2]:
        apply_btn = st.button("Apply", type="primary", use_container_width=True, disabled=not tf_init or job_running)
    with tf_cols[3]:
        destroy_btn = st.button(
            "Destroy", type="primary", key="deploy_destroy",
            use_container_width=True, disabled=not tf_init or job_running,
        )

    if destroy_btn and not run_destroy:
        st.session_state.show_destroy_dialog = True

    if st.session_state.show_destroy_dialog and not run_destroy:
        destroy_confirm_dialog()

    section("ssh")
    st.caption("After redeploying VMs, clear stale SSH host keys so Ansible can reconnect.")
    clean_btn = st.button("Clear SSH keys", key="deploy_clean_hosts", disabled=job_running)

    section("output")
    if job_running:
        st.caption("Job running on server — safe to refresh or reconnect; output updates automatically.")

    deploy_terminal = st.fragment(run_every=timedelta(seconds=2))(_deploy_terminal_fragment)
    deploy_terminal()

    def queue_deploy(cmd: str, cwd: str, ok_msg: str, err_msg: str):
        if not start_deploy_job(cmd, cwd, ok_msg, err_msg):
            st.warning("A deploy job is already running.")
        else:
            st.rerun()

    if run_destroy:
        st.session_state.show_destroy_dialog = False
        if not st.session_state.get("destroy_ui_flushed"):
            st.session_state.destroy_ui_flushed = True
            st.rerun()
        st.session_state.pop("run_destroy", None)
        st.session_state.pop("destroy_ui_flushed", None)
        queue_deploy("terraform destroy -auto-approve -no-color", TERRAFORM_DIR, "Destroyed", "Destroy failed")
    elif init_btn:
        queue_deploy("terraform init -upgrade -no-color", TERRAFORM_DIR, "Init complete", "Init failed")
    elif plan_btn:
        queue_deploy("terraform plan -no-color", TERRAFORM_DIR, "Plan complete", "Plan failed")
    elif apply_btn:
        queue_deploy("terraform apply -auto-approve -no-color", TERRAFORM_DIR, "Infrastructure deployed", "Apply failed")
    elif clean_btn:
        if not file_exists(CLEAN_HOSTS_SCRIPT):
            st.session_state.deploy_output = f"$ Clear SSH keys\n\nScript not found: {CLEAN_HOSTS_SCRIPT}\n"
            st.session_state.deploy_status = ("error", "Script not found")
            write_deploy_status("error", "Script not found")
            with open(DEPLOY_LOG, "w") as f:
                f.write(st.session_state.deploy_output)
            st.rerun()
        else:
            os.chmod(CLEAN_HOSTS_SCRIPT, 0o755)
            queue_deploy(f'"{CLEAN_HOSTS_SCRIPT}"', BASE_DIR, "SSH keys cleared", "Failed to clear SSH keys")


def _playbooks_tab():
    sync_all_playbooks_from_disk()
    jobs_busy = is_any_playbook_job_running() or is_deploy_job_running()

    if jobs_busy:
        st.caption("Playbook running on server — safe to refresh or reconnect; output updates automatically.")

    for i, (pb_file, pb_desc, color) in enumerate(PLAYBOOKS):
        key = playbook_job_key(pb_file)
        with st.container(border=True):
            card_col, run_col = st.columns([6, 1], gap="small", vertical_alignment="center")
            with card_col:
                st.markdown(pb_card_html(i + 1, pb_desc, pb_file, color), unsafe_allow_html=True)
            with run_col:
                run_btn = st.button(
                    "Run", key=f"run_{pb_file}", use_container_width=True,
                    disabled=jobs_busy and not is_playbook_job_running(key),
                )

            if run_btn:
                cmd = f"ansible-playbook -i inventory/hosts.ini playbooks/{pb_file}"
                if start_playbook_job(key, cmd, ANSIBLE_DIR, "complete", "failed", pb_file=pb_file):
                    st.rerun()
                else:
                    st.warning("A playbook is already running.")

            if playbook_has_output(pb_file) or is_playbook_job_running(key):
                status = read_playbook_status(key)
                render_terminal(
                    st.empty(),
                    read_playbook_log(key) or st.session_state.playbook_outputs.get(pb_file, ""),
                    state=status.get("state", "idle"),
                    footer=status.get("footer", "ready"),
                    title=f"cyberlab@ansible — {pb_file}",
                    extra_class="term-in-card",
                    term_id=f"pb:{pb_file}",
                )


def _batch_playbooks_tab():
    poll_playbook_job(BATCH_PLAYBOOK_KEY)
    batch_status = read_playbook_status(BATCH_PLAYBOOK_KEY)
    batch_log = read_playbook_log(BATCH_PLAYBOOK_KEY)
    batch_running = is_playbook_job_running(BATCH_PLAYBOOK_KEY)
    jobs_busy = is_any_playbook_job_running() or is_deploy_job_running()

    section("batch execution")
    clean_first = st.checkbox("Clear SSH keys before running", value=True)
    exclude = st.multiselect("Exclude", options=[d for _, d, _ in PLAYBOOKS])
    run_all = st.button(
        "Execute All", type="primary", use_container_width=True,
        disabled=jobs_busy and not batch_running,
    )

    if batch_log or batch_running:
        if batch_running:
            st.caption("Batch job running on server — safe to refresh or reconnect.")
        render_terminal(
            st.empty(),
            batch_log,
            state=batch_status.get("state", "idle"),
            footer=batch_status.get("footer", "ready"),
            title="cyberlab@ansible — batch",
            extra_class="term-in-card",
            term_id="pb:batch",
        )

    if run_all:
        if jobs_busy and not batch_running:
            st.warning("Another job is already running.")
            return

        pb_files = [f for f, d, _ in PLAYBOOKS if d not in exclude]
        if not pb_files:
            st.warning("No playbooks selected.")
            return

        if clean_first:
            if not file_exists(CLEAN_HOSTS_SCRIPT):
                st.error(f"Script not found: {CLEAN_HOSTS_SCRIPT}")
                return
            os.chmod(CLEAN_HOSTS_SCRIPT, 0o755)
            rc, _ = run_command(f'"{CLEAN_HOSTS_SCRIPT}"', BASE_DIR, st.empty())
            if rc != 0:
                st.error("Failed to clear SSH keys. Stopping.")
                return
            st.success("SSH keys cleared")

        parts = []
        for pb in pb_files:
            parts.append(f'echo "" && echo "=== {pb} ==="')
            parts.append(f"ansible-playbook -i inventory/hosts.ini playbooks/{pb}")
        batch_cmd = " && ".join(parts)
        if start_playbook_job(
            BATCH_PLAYBOOK_KEY, batch_cmd, ANSIBLE_DIR,
            "All playbooks complete", "Batch failed", running_label="batch",
        ):
            st.rerun()
        else:
            st.warning("A playbook job is already running.")


def page_ansible():
    st.markdown(hero("Ansible"), unsafe_allow_html=True)
    st.markdown('<div class="hero-sub">Configure software & security stack</div>', unsafe_allow_html=True)

    if "playbook_outputs" not in st.session_state:
        st.session_state.playbook_outputs = {}
    if "playbook_status" not in st.session_state:
        st.session_state.playbook_status = {}

    sync_all_playbooks_from_disk()

    section("ssh")
    st.caption("Clear stale SSH host keys before connecting to redeployed Linux VMs.")
    if st.button(
        "Clear SSH keys", key="ansible_clean_hosts",
        disabled=is_any_playbook_job_running() or is_deploy_job_running(),
    ):
        out = st.empty()
        rc, _ = run_clean_known_hosts(out)
        st.success("SSH keys cleared") if rc == 0 else st.error("Failed to clear SSH keys")

    tab1, tab2 = st.tabs(["Playbooks", "Run All"])

    with tab1:
        playbooks_tab = st.fragment(run_every=timedelta(seconds=2))(_playbooks_tab)
        playbooks_tab()

    with tab2:
        batch_tab = st.fragment(run_every=timedelta(seconds=2))(_batch_playbooks_tab)
        batch_tab()


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------

st.set_page_config(page_title="CyberLab", page_icon="terminal", layout="wide", initial_sidebar_state="expanded")
st.markdown(THEME_CSS, unsafe_allow_html=True)
inject_terminal_autoscroll()

with st.sidebar:
    st.markdown("""<div style="padding: 8px 0 16px 0;">
        <span style="font-family:'JetBrains Mono',monospace;font-size:1.5rem;font-weight:700;color:#3fb950;">Cyber</span><span style="font-family:'JetBrains Mono',monospace;font-size:1.5rem;font-weight:700;color:#e6edf3;">Lab</span>
        <div style="font-family:'JetBrains Mono',monospace;font-size:0.6rem;color:#484f58;margin-top:2px;letter-spacing:0.15em;">INFRASTRUCTURE MANAGER</div>
    </div>""", unsafe_allow_html=True)
    st.markdown('<div style="height:1px;background:linear-gradient(90deg,rgba(48,54,61,0.9),transparent);margin-bottom:8px;"></div>', unsafe_allow_html=True)

    page = st.radio(
        "nav",
        ["Dashboard", "Terraform Config", "VM Editor", "Ansible Secrets", "Deploy", "Ansible Playbooks"],
        label_visibility="collapsed",
    )

    st.markdown('<div style="height:1px;background:linear-gradient(90deg,rgba(48,54,61,0.6),transparent);margin:12px 0 8px;"></div>', unsafe_allow_html=True)
    st.markdown('<div style="font-family:\'JetBrains Mono\',monospace;font-size:0.55rem;color:#21262d;letter-spacing:0.1em;">v1.0 // frostsec</div>', unsafe_allow_html=True)

PAGES = {
    "Dashboard": page_dashboard,
    "Terraform Config": page_terraform_config,
    "VM Editor": page_vm_editor,
    "Ansible Secrets": page_ansible_secrets,
    "Deploy": page_deploy,
    "Ansible Playbooks": page_ansible,
}

PAGES[page]()
