#!/usr/bin/env python3
import os
import sys

# macOS: Streamlit loads ObjC; fork() in subprocess without this aborts the parent (SIGABRT).
if sys.platform == "darwin":
    os.environ.setdefault("OBJC_DISABLE_INITIALIZE_FORK_SAFETY", "YES")

import html
import re
import signal
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

from cyberlab_common import ansible_playbook_cmd

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TERRAFORM_DIR = os.path.join(BASE_DIR, "terraform")
ANSIBLE_DIR = os.path.join(BASE_DIR, "ansible")
CYBERLAB_DIR = os.path.join(BASE_DIR, ".cyberlab")
UI_CONFIG_FILE = os.path.join(CYBERLAB_DIR, "ui_config.json")
PLAYBOOKS_JOB_DIR = os.path.join(CYBERLAB_DIR, "playbooks")
BATCH_PLAYBOOK_KEY = "batch"
CLEAN_HOSTS_KEY = "clean_hosts"
ANSIBLE_TERMINAL_CACHE = "ansible"
DEPLOY_LOG = os.path.join(CYBERLAB_DIR, "deploy.log")
DEPLOY_STATUS_FILE = os.path.join(CYBERLAB_DIR, "deploy.status.json")
DEPLOY_EXIT_FILE = os.path.join(CYBERLAB_DIR, "deploy.exit")
CLEAN_HOSTS_SCRIPT = os.path.join(BASE_DIR, "scripts", "clean_known_hosts.sh")
ROUTER_VM = "PF-01-RTR"
DC_VM = "DC-01-SRV"

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
    padding: 8px 18px;
    box-sizing: border-box;
    min-height: 2.75rem;
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
    align-items: center !important;
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

.stApp div[data-testid="stVerticalBlockBorderWrapper"]:has(.pb-card-inner) [data-testid="stHorizontalBlock"] > div[data-testid="column"]:nth-child(2) {
    flex: 0 0 auto !important;
    width: auto !important;
    min-width: 72px !important;
    align-self: stretch !important;
    border-left: 1px solid var(--border) !important;
    display: flex !important;
    align-items: center !important;
    justify-content: center !important;
}

.stApp div[data-testid="stVerticalBlockBorderWrapper"]:has(.pb-card-inner) [data-testid="stHorizontalBlock"] > div[data-testid="column"]:nth-child(2) > div[data-testid="stVerticalBlock"] {
    width: 100% !important;
    height: 100% !important;
    justify-content: center !important;
    align-items: center !important;
}

.stApp div[data-testid="stVerticalBlockBorderWrapper"]:has(.pb-card-inner) [data-testid="stHorizontalBlock"] > div[data-testid="column"]:nth-child(2) [data-testid="stMarkdownContainer"] {
    margin: 0 !important;
    padding: 0 10px !important;
    display: flex !important;
    align-items: center !important;
    justify-content: center !important;
}

.stApp div[data-testid="stVerticalBlockBorderWrapper"]:has(.pb-card-inner) [data-testid="stHorizontalBlock"] > div[data-testid="column"]:last-child {
    flex: 0 0 72px !important;
    width: 72px !important;
    min-width: 72px !important;
    max-width: 72px !important;
    align-self: stretch !important;
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
    height: 2rem !important;
    min-height: 2rem !important;
    width: 100% !important;
    margin: 0 !important;
    padding: 0 10px !important;
    border-radius: 0 !important;
    font-size: 0.72rem !important;
    display: inline-flex !important;
    align-items: center !important;
    justify-content: center !important;
    box-sizing: border-box !important;
}

.stApp div[data-testid="stVerticalBlockBorderWrapper"]:has(.pb-card-inner) [data-testid="stHorizontalBlock"] > div[data-testid="column"]:last-child div[data-testid="stButton"] > button:not([kind="primary"]):not([data-testid="baseButton-primary"]) {
    border: none !important;
    background: var(--bg-elevated) !important;
}

.stApp div[data-testid="stVerticalBlockBorderWrapper"]:has(.pb-card-inner):hover {
    border-color: rgba(63, 185, 80, 0.35) !important;
}

.stApp div[data-testid="stVerticalBlockBorderWrapper"]:has(.pb-card-inner) [data-testid="stHorizontalBlock"] > div[data-testid="column"]:last-child div[data-testid="stButton"] > button:hover:not([data-testid="baseButton-primary"]):not([kind="primary"]) {
    background: rgba(255, 255, 255, 0.06) !important;
}

.pb-dot {
    width: 10px;
    height: 10px;
    border-radius: 50%;
    flex-shrink: 0;
}

.pb-info { flex: 1; min-width: 0; }

.pb-state {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.58rem;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    height: 2rem;
    padding: 0 10px;
    border-radius: 999px;
    border: 1px solid var(--border);
    white-space: nowrap;
    box-sizing: border-box;
    line-height: 1;
}

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

.metric-big.metric-pass { color: #3fb950; }
.metric-big.metric-fail { color: #f85149; }
.metric-big.metric-warn { color: #d29922; }
.metric-big.metric-muted { color: #484f58; }

.pb-state.passed {
    color: #3fb950;
    border-color: rgba(63, 185, 80, 0.35);
    background: rgba(63, 185, 80, 0.08);
}

.pb-state.failed {
    color: #f85149;
    border-color: rgba(248, 81, 73, 0.35);
    background: rgba(248, 81, 73, 0.08);
}

.pb-state.stopped {
    color: #d29922;
    border-color: rgba(210, 153, 34, 0.35);
    background: rgba(210, 153, 34, 0.08);
}

.pb-state.running {
    color: #d29922;
    border-color: rgba(210, 153, 34, 0.35);
    background: rgba(210, 153, 34, 0.08);
}

.pb-state.pending {
    color: #6e7681;
    border-color: rgba(48, 54, 61, 0.9);
    background: rgba(255, 255, 255, 0.02);
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
.stApp div.stButton > button[kind="primary"],
.stApp div[data-testid="stButton"] > button[data-testid="baseButton-primary"],
.stApp div.stButton > button[data-testid="baseButton-primary"] {
    background: var(--accent) !important;
    color: #ffffff !important;
    border: 1px solid var(--accent) !important;
    font-weight: 600 !important;
}

.stApp div[data-testid="stButton"] > button[kind="primary"]:hover,
.stApp div.stButton > button[kind="primary"]:hover,
.stApp div[data-testid="stButton"] > button[data-testid="baseButton-primary"]:hover,
.stApp div.stButton > button[data-testid="baseButton-primary"]:hover {
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

.stApp [class*="st-key-run_"] div[data-testid="stButton"] > button,
.stApp [class*="st-key-run_"] div[data-testid="stButton"] > button[data-testid="baseButton-primary"] {
    background: var(--accent) !important;
    border: 1px solid var(--accent) !important;
    color: #ffffff !important;
    font-weight: 600 !important;
}

.stApp [class*="st-key-run_"] div[data-testid="stButton"] > button:hover:not(:disabled),
.stApp [class*="st-key-run_"] div[data-testid="stButton"] > button[data-testid="baseButton-primary"]:hover:not(:disabled) {
    background: var(--accent-dim) !important;
    border-color: var(--accent-dim) !important;
    color: #ffffff !important;
}

.stApp [class*="st-key-stop_"] div[data-testid="stButton"] > button,
.stApp [class*="st-key-stop_"] div[data-testid="stButton"] > button[data-testid="baseButton-primary"],
.stApp .st-key-batch_stop div[data-testid="stButton"] > button,
.stApp .st-key-batch_stop div[data-testid="stButton"] > button[data-testid="baseButton-primary"] {
    background: #da3633 !important;
    border: 1px solid #da3633 !important;
    color: #ffffff !important;
    font-weight: 600 !important;
}

.stApp [class*="st-key-stop_"] div[data-testid="stButton"] > button:hover:not(:disabled),
.stApp [class*="st-key-stop_"] div[data-testid="stButton"] > button[data-testid="baseButton-primary"]:hover:not(:disabled),
.stApp .st-key-batch_stop div[data-testid="stButton"] > button:hover:not(:disabled),
.stApp .st-key-batch_stop div[data-testid="stButton"] > button[data-testid="baseButton-primary"]:hover:not(:disabled) {
    background: #b62324 !important;
    border-color: #b62324 !important;
    color: #ffffff !important;
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

.topo-wrap {
    margin: 1rem 0 1.5rem 0;
    font-family: 'JetBrains Mono', monospace;
}

.topo-stack {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 0;
}

.topo-wan {
    background: rgba(56, 173, 255, 0.1);
    border: 1px solid rgba(56, 173, 255, 0.35);
    border-radius: 8px;
    padding: 12px 24px;
    text-align: center;
    min-width: 200px;
}

.topo-wan-label {
    font-size: 0.72rem;
    font-weight: 600;
    color: #38adff;
    text-transform: uppercase;
    letter-spacing: 0.08em;
}

.topo-wan-ip {
    font-size: 0.78rem;
    color: #c9d1d9;
    margin-top: 4px;
}

.topo-vline {
    width: 2px;
    height: 28px;
    background: linear-gradient(180deg, rgba(56, 173, 255, 0.5), rgba(63, 185, 80, 0.5));
}

.topo-router {
    background: rgba(63, 185, 80, 0.1);
    border: 1px solid rgba(63, 185, 80, 0.45);
    border-radius: 8px;
    padding: 14px 22px;
    text-align: center;
    min-width: 220px;
}

.topo-router-name {
    font-size: 0.85rem;
    font-weight: 700;
    color: #3fb950;
    margin-bottom: 6px;
}

.topo-router-iface {
    font-size: 0.7rem;
    color: #8b949e;
    line-height: 1.6;
}

.topo-router-iface code {
    color: #a5d6ff;
    font-size: 0.68rem;
}

.topo-lan-zone {
    width: 100%;
    margin-top: 0;
    border: 1px dashed rgba(63, 185, 80, 0.35);
    border-radius: 10px;
    padding: 18px 16px 16px;
    background: rgba(22, 27, 34, 0.5);
    box-sizing: border-box;
}

.topo-zone-label {
    text-align: center;
    font-size: 0.65rem;
    color: #6e7681;
    text-transform: uppercase;
    letter-spacing: 0.12em;
    margin-bottom: 16px;
}

.topo-dc {
    display: flex;
    flex-direction: column;
    align-items: center;
    margin: 0 auto 12px;
    max-width: 280px;
    background: rgba(88, 166, 255, 0.1);
    border: 1px solid rgba(88, 166, 255, 0.4);
    border-radius: 8px;
    padding: 12px 18px;
    text-align: center;
}

.topo-dc-badge {
    display: inline-block;
    font-size: 0.58rem;
    font-weight: 700;
    letter-spacing: 0.1em;
    color: #58a6ff;
    background: rgba(88, 166, 255, 0.15);
    border: 1px solid rgba(88, 166, 255, 0.35);
    border-radius: 4px;
    padding: 2px 8px;
    margin-bottom: 6px;
}

.topo-dc-name {
    font-size: 0.82rem;
    font-weight: 600;
    color: #e6edf3;
}

.topo-dc-role {
    font-size: 0.62rem;
    color: #58a6ff;
    margin-top: 2px;
}

.topo-dc-ip {
    font-size: 0.68rem;
    color: #8b949e;
    margin-top: 4px;
}

.topo-dc-ip code {
    color: #a5d6ff;
}

.topo-join {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 10px;
    margin: 8px 0 14px;
    font-size: 0.6rem;
    color: #484f58;
    text-transform: uppercase;
    letter-spacing: 0.1em;
}

.topo-join::before,
.topo-join::after {
    content: "";
    flex: 1;
    max-width: 120px;
    height: 1px;
    background: linear-gradient(90deg, transparent, rgba(88, 166, 255, 0.35), transparent);
}

.topo-members {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(140px, 1fr));
    gap: 10px;
}

.topo-member {
    position: relative;
    background: var(--bg-card);
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 10px 12px;
    text-align: center;
}

.topo-member::before {
    content: "";
    position: absolute;
    top: -14px;
    left: 50%;
    width: 1px;
    height: 14px;
    background: rgba(88, 166, 255, 0.25);
}

.topo-member-name {
    font-size: 0.72rem;
    font-weight: 600;
    color: #c9d1d9;
    word-break: break-word;
}

.topo-member-ip {
    font-size: 0.65rem;
    color: #6e7681;
    margin-top: 3px;
}

.topo-member-ip code {
    color: #8b949e;
    font-size: 0.62rem;
}

.topo-member-join {
    font-size: 0.55rem;
    color: #484f58;
    margin-top: 4px;
    text-transform: uppercase;
    letter-spacing: 0.06em;
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


def read_ui_config() -> dict:
    if not file_exists(UI_CONFIG_FILE):
        return {}
    try:
        with open(UI_CONFIG_FILE) as f:
            return json.load(f)
    except Exception:
        return {}


def write_ui_config(config: dict):
    ensure_cyberlab_dir()
    with open(UI_CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=4)


def default_router_ips() -> dict[str, str]:
    return {"lan": "172.16.10.1/24", "wan": ""}


def get_router_ips(config: dict | None = None) -> dict[str, str]:
    cfg = config if config is not None else read_ui_config()
    defaults = default_router_ips()
    stored = cfg.get("router_ips", {})
    return {
        "lan": stored.get("lan", defaults["lan"]),
        "wan": stored.get("wan", defaults["wan"]),
    }


def parse_disk_size_gb(size: str) -> float:
    if not size:
        return 0.0
    match = re.match(r"^(\d+(?:\.\d+)?)\s*([GMTK]?)(?:i?B)?$", size.strip(), re.I)
    if not match:
        return 0.0
    value = float(match.group(1))
    unit = match.group(2).upper()
    multipliers = {"": 1.0, "K": 1 / 1024 / 1024, "M": 1 / 1024, "G": 1.0, "T": 1024.0}
    return value * multipliers.get(unit, 1.0)


def total_disk_gb(vms: list) -> float:
    total = 0.0
    for vm in vms:
        for disk in vm.get("disks", []):
            if disk.get("type") == "disk":
                total += parse_disk_size_gb(disk.get("size", ""))
    return total


def format_disk_gb(gb: float) -> str:
    if gb >= 1024:
        return f"{gb / 1024:.1f}T"
    if gb == int(gb):
        return f"{int(gb)}G"
    return f"{gb:.1f}G"


def vm_topology_ip(vm: dict, router_ips: dict[str, str]) -> str:
    if vm.get("name") == ROUTER_VM:
        lan = html.escape(router_ips.get("lan") or "—")
        wan = html.escape(router_ips.get("wan") or "—")
        return f'LAN <code>{lan}</code><br>WAN <code>{wan}</code>'
    ci = vm.get("cloudinit", {})
    if ci.get("enabled") and ci.get("ipconfig"):
        ip = html.escape(ci["ipconfig"][0].get("ip", "") or "—")
        return f"<code>{ip}</code>"
    return "—"


def vm_short_ip(vm: dict) -> str:
    ci = vm.get("cloudinit", {})
    if ci.get("enabled") and ci.get("ipconfig"):
        ip = ci["ipconfig"][0].get("ip", "")
        return ip.split("/")[0] if ip else ""
    return ""


def lan_network_label(router_ips: dict[str, str]) -> str:
    lan = router_ips.get("lan", "172.16.10.1/24")
    if "/" in lan:
        host, mask = lan.split("/", 1)
        prefix = host.rsplit(".", 1)[0]
        return f"{prefix}.0/{mask}"
    return "172.16.10.0/24"


def render_topology_graph(vms: list, router_ips: dict[str, str]) -> str:
    dc = next((v for v in vms if v.get("name") == DC_VM), None)
    members = [v for v in vms if v.get("name") not in (ROUTER_VM, DC_VM)]

    lan = html.escape(router_ips.get("lan") or "—")
    wan = html.escape(router_ips.get("wan") or "—")
    lan_net = html.escape(lan_network_label(router_ips))

    member_nodes = ""
    for vm in members:
        name = html.escape(vm["name"])
        ip = html.escape(vm_short_ip(vm) or "—")
        member_nodes += (
            f'<div class="topo-member">'
            f'<div class="topo-member-name">{name}</div>'
            f'<div class="topo-member-ip"><code>{ip}</code></div>'
            f'<div class="topo-member-join">joined to {html.escape(DC_VM)}</div>'
            f'</div>'
        )

    dc_block = ""
    if dc:
        dc_ip = html.escape(vm_short_ip(dc) or "—")
        dc_block = f'''<div class="topo-dc">
            <span class="topo-dc-badge">DC</span>
            <div class="topo-dc-name">{html.escape(DC_VM)}</div>
            <div class="topo-dc-role">Domain Controller</div>
            <div class="topo-dc-ip"><code>{dc_ip}</code></div>
        </div>'''

    return f'''<div class="topo-wrap">
<div class="topo-stack">
  <div class="topo-wan">
    <div class="topo-wan-label">WAN · vmbr0</div>
    <div class="topo-wan-ip"><code>{wan}</code></div>
  </div>
  <div class="topo-vline"></div>
  <div class="topo-router">
    <div class="topo-router-name">{html.escape(ROUTER_VM)}</div>
    <div class="topo-router-iface">WAN <code>{wan}</code><br>LAN <code>{lan}</code></div>
  </div>
  <div class="topo-vline"></div>
  <div class="topo-lan-zone">
    <div class="topo-zone-label">LAN · vmbr1 · {lan_net}</div>
    {dc_block}
    <div class="topo-join">domain joined</div>
    <div class="topo-members">{member_nodes}</div>
  </div>
</div>
</div>'''


def process_running(pid: int | None) -> bool:
    if not pid:
        return False
    try:
        cpid, _ = os.waitpid(pid, os.WNOHANG)
        if cpid == pid:
            return False
    except ChildProcessError:
        return False
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    return True


def read_exit_code(exit_path: str) -> int | None:
    if not file_exists(exit_path):
        return None
    try:
        raw = open(exit_path).read().strip()
        return int(raw) if raw != "" else None
    except Exception:
        return None


def append_completion_log(log_path: str, rc: int, ok_msg: str, err_msg: str):
    if not log_path:
        return
    marker = "--- cyberlab job complete ---"
    if file_exists(log_path):
        with open(log_path) as f:
            if marker in f.read():
                return
    line = f"\n{marker}\n[OK] {ok_msg}\n" if rc == 0 else f"\n{marker}\n[ERROR] {err_msg}\n"
    with open(log_path, "a") as f:
        f.write(line)


def render_terminal_cached(cache_key: str, placeholder, *, force: bool = False, **kwargs):
    sig = (
        kwargs.get("text", ""),
        kwargs.get("state"),
        kwargs.get("footer"),
        kwargs.get("title"),
        kwargs.get("extra_class"),
        kwargs.get("term_id"),
    )
    state_key = f"term_cache_{cache_key}"
    if not force and st.session_state.get(state_key) == sig:
        return
    st.session_state[state_key] = sig
    render_terminal(placeholder, **kwargs)


def set_ansible_terminal_focus(key: str, title: str):
    st.session_state.ansible_terminal_key = key
    st.session_state.ansible_terminal_title = title
    st.session_state.pop(f"term_cache_{ANSIBLE_TERMINAL_CACHE}", None)


def is_ansible_busy() -> bool:
    if is_deploy_job_running():
        return True
    if is_playbook_job_running(CLEAN_HOSTS_KEY):
        return True
    if is_playbook_job_running(BATCH_PLAYBOOK_KEY):
        return True
    return any(is_playbook_job_running(playbook_job_key(pb_file)) for pb_file, _, _ in PLAYBOOKS)


def resolve_ansible_terminal() -> tuple[str, dict, str]:
    candidates: list[tuple[str, str]] = [
        (CLEAN_HOSTS_KEY, "cyberlab@ansible — clean ssh keys"),
        (BATCH_PLAYBOOK_KEY, "cyberlab@ansible — batch"),
    ]
    candidates += [
        (playbook_job_key(pb_file), f"cyberlab@ansible — {pb_file}")
        for pb_file, _, _ in PLAYBOOKS
    ]

    for key, title in candidates:
        if is_playbook_job_running(key):
            return read_playbook_log(key), read_playbook_status(key), title

    for key, title in candidates:
        status = read_playbook_status(key)
        paths = playbook_job_paths(key)
        if status.get("state") in ("running", "success", "error", "stopped") and file_exists(paths["log"]):
            return read_playbook_log(key), status, title

    key = st.session_state.get("ansible_terminal_key", "")
    if key:
        paths = playbook_job_paths(key)
        if file_exists(paths["log"]):
            return (
                read_playbook_log(key),
                read_playbook_status(key),
                st.session_state.get("ansible_terminal_title", "cyberlab@ansible"),
            )

    return "", {"state": "idle", "footer": "ready"}, "cyberlab@ansible — zsh"


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

    rc = read_exit_code(DEPLOY_EXIT_FILE)
    if rc is None and process_running(status.get("pid")):
        return status
    if rc is None:
        rc = 1

    ok_msg = status.get("ok_msg") or "complete"
    err_msg = status.get("err_msg") or "failed"
    append_completion_log(DEPLOY_LOG, rc, ok_msg, err_msg)
    if rc == 0:
        write_deploy_status("success", ok_msg, cmd=status.get("cmd"), ok_msg=ok_msg, err_msg=err_msg)
    else:
        write_deploy_status("error", err_msg, cmd=status.get("cmd"), ok_msg=ok_msg, err_msg=err_msg)
    return read_deploy_status()


def sync_deploy_from_disk() -> bool:
    before = read_deploy_status().get("state")
    status = poll_deploy_job()
    st.session_state.deploy_output = read_deploy_log()
    st.session_state.deploy_status = (status.get("state", "idle"), status.get("footer", "ready"))
    after = status.get("state")
    return before == "running" and after != "running"


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
    st.session_state.pop("term_cache_deploy", None)
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
    if process_running(status.get("pid")):
        return True
    paths = playbook_job_paths(key)
    return not file_exists(paths["exit"])


def is_any_playbook_job_running() -> bool:
    if is_playbook_job_running(BATCH_PLAYBOOK_KEY):
        return True
    return any(is_playbook_job_running(playbook_job_key(pb_file)) for pb_file, _, _ in PLAYBOOKS)


def poll_playbook_job(key: str) -> dict:
    status = read_playbook_status(key)
    if status.get("state") != "running":
        return status

    paths = playbook_job_paths(key)
    rc = read_exit_code(paths["exit"])
    if rc is None and process_running(status.get("pid")):
        return status
    if rc is None and not file_exists(paths["exit"]):
        return status
    if rc is None:
        rc = 1

    ok_msg = status.get("ok_msg") or "complete"
    err_msg = status.get("err_msg") or "failed"
    append_completion_log(paths["log"], rc, ok_msg, err_msg)
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


def clear_terminal_caches():
    for k in list(st.session_state.keys()):
        if isinstance(k, str) and k.startswith("term_cache_"):
            del st.session_state[k]


def sync_all_playbooks_from_disk() -> bool:
    """Sync playbook state from disk. Returns True if a job just finished."""
    finished = False
    for pb_file, _, _ in PLAYBOOKS:
        key = playbook_job_key(pb_file)
        before = read_playbook_status(key).get("state")
        poll_playbook_job(key)
        after = read_playbook_status(key).get("state")
        if before == "running" and after != "running":
            finished = True
        paths = playbook_job_paths(key)
        if file_exists(paths["log"]) or file_exists(paths["status"]):
            st.session_state.playbook_outputs[pb_file] = read_playbook_log(key)
            status = read_playbook_status(key)
            st.session_state.playbook_status[pb_file] = (
                status.get("state", "idle"), status.get("footer", "ready")
            )

    before = read_playbook_status(BATCH_PLAYBOOK_KEY).get("state")
    poll_playbook_job(BATCH_PLAYBOOK_KEY)
    after = read_playbook_status(BATCH_PLAYBOOK_KEY).get("state")
    if before == "running" and after != "running":
        finished = True
    return finished


def playbook_has_output(pb_file: str) -> bool:
    key = playbook_job_key(pb_file)
    paths = playbook_job_paths(key)
    return file_exists(paths["log"]) or pb_file in st.session_state.get("playbook_outputs", {})


def playbook_run_state(pb_file: str) -> str:
    key = playbook_job_key(pb_file)
    state = read_playbook_status(key).get("state", "idle")
    if state == "running" or is_playbook_job_running(key):
        return "running"
    if state == "stopped":
        return "stopped"
    if state in ("success", "error"):
        return state
    return "pending"


def get_playbook_run_stats() -> dict:
    passed = failed = pending = running = 0
    for pb_file, _, _ in PLAYBOOKS:
        state = playbook_run_state(pb_file)
        if state == "success":
            passed += 1
        elif state in ("error", "stopped"):
            failed += 1
        elif state == "running":
            running += 1
        else:
            pending += 1
    total = len(PLAYBOOKS)
    ran = passed + failed
    return {
        "total": total,
        "ran": ran,
        "passed": passed,
        "failed": failed,
        "pending": pending,
        "running": running,
    }


def render_playbook_stats():
    stats = get_playbook_run_stats()
    c1, c2, c3, c4, c5 = st.columns(5)
    with c1:
        st.markdown(
            f'<div class="metric-big">{stats["total"]}</div><div class="metric-label">Total</div>',
            unsafe_allow_html=True,
        )
    with c2:
        st.markdown(
            f'<div class="metric-big">{stats["ran"]}</div><div class="metric-label">Ran</div>',
            unsafe_allow_html=True,
        )
    with c3:
        st.markdown(
            f'<div class="metric-big metric-pass">{stats["passed"]}</div><div class="metric-label">Passed</div>',
            unsafe_allow_html=True,
        )
    with c4:
        st.markdown(
            f'<div class="metric-big metric-fail">{stats["failed"]}</div><div class="metric-label">Failed</div>',
            unsafe_allow_html=True,
        )
    with c5:
        pending_label = "Pending" if stats["running"] == 0 else "Pending / Running"
        pending_value = stats["pending"] if stats["running"] == 0 else f'{stats["pending"]} / {stats["running"]}'
        pending_class = "metric-muted" if stats["running"] == 0 else "metric-warn"
        st.markdown(
            f'<div class="metric-big {pending_class}">{pending_value}</div><div class="metric-label">{pending_label}</div>',
            unsafe_allow_html=True,
        )


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
    st.session_state.pop(f"term_cache_pb_{key}", None)
    return True


def stop_playbook_job(key: str) -> bool:
    status = read_playbook_status(key)
    if status.get("state") != "running":
        return False

    paths = playbook_job_paths(key)
    pid = status.get("pid")
    if pid:
        try:
            os.killpg(os.getpgid(pid), signal.SIGTERM)
        except (OSError, ProcessLookupError):
            try:
                os.kill(pid, signal.SIGTERM)
            except (OSError, ProcessLookupError):
                pass

    time.sleep(0.3)
    if pid and process_running(pid):
        try:
            os.killpg(os.getpgid(pid), signal.SIGKILL)
        except (OSError, ProcessLookupError):
            try:
                os.kill(pid, signal.SIGKILL)
            except (OSError, ProcessLookupError):
                pass

    with open(paths["exit"], "w") as f:
        f.write("130")
    append_completion_log(paths["log"], 130, "", "Stopped by user")
    write_playbook_status(
        key,
        "stopped",
        "stopped",
        cmd=status.get("cmd"),
        ok_msg=status.get("ok_msg", ""),
        err_msg="Stopped by user",
        pb_file=status.get("pb_file"),
    )
    pb_file = status.get("pb_file")
    if pb_file:
        st.session_state.playbook_outputs[pb_file] = read_playbook_log(key)
        st.session_state.playbook_status[pb_file] = ("stopped", "stopped")
    st.session_state.pop(f"term_cache_pb_{key}", None)
    return True


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
            elif stripped.startswith("[OK]"):
                content = f'<span class="t-add">{html.escape(line)}</span>'
            elif stripped.startswith("[ERROR]"):
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

  let syncTimer;
  function syncTerminalsDebounced() {
    clearTimeout(syncTimer);
    syncTimer = setTimeout(syncTerminals, 150);
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

  const obs = new MutationObserver(() => syncTerminalsDebounced());
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


def pb_state_html(state: str = "pending") -> str:
    state_labels = {
        "success": ("passed", "passed"),
        "error": ("failed", "failed"),
        "stopped": ("stopped", "stopped"),
        "running": ("running", "running"),
        "pending": ("pending", "pending"),
    }
    label, css = state_labels.get(state, ("pending", "pending"))
    return f'<span class="pb-state {css}">{label}</span>'


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

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.markdown(f'<div class="metric-big">{len(vms)}</div><div class="metric-label">VMs Defined</div>', unsafe_allow_html=True)
    with col2:
        st.markdown(f'<div class="metric-big">{vm_count}</div><div class="metric-label">VMs Deployed</div>', unsafe_allow_html=True)
    with col3:
        total_ram = sum(v.get("memory", 0) for v in vms)
        st.markdown(f'<div class="metric-big">{total_ram // 1024}G</div><div class="metric-label">Total RAM</div>', unsafe_allow_html=True)
    with col4:
        total_disk = format_disk_gb(total_disk_gb(vms))
        st.markdown(f'<div class="metric-big">{total_disk}</div><div class="metric-label">Total Disk</div>', unsafe_allow_html=True)

    if vms:
        section("lab topology")
        router_ips = get_router_ips()
        st.markdown(render_topology_graph(vms, router_ips), unsafe_allow_html=True)
        rows = ""
        for vm in vms:
            deps = vm.get("depends_on", [])
            tn = 0 if not deps else (1 if len(deps) == 1 else 2)
            ct = "linked" if not vm.get("full_clone", True) else "full"
            disk = next((d.get("size", "") for d in vm.get("disks", []) if d.get("type") == "disk"), "")
            ip = vm_topology_ip(vm, router_ips)
            rows += f'<tr><td><span class="tier-badge tier-{tn}">T{tn}</span></td><td><strong>{vm["name"]}</strong></td><td>{vm["vmid"]}</td><td>{vm.get("clone","")}</td><td>{vm.get("cpu",{}).get("cores","")}c / {vm.get("memory","")}M</td><td>{disk}</td><td class="clone-{ct}">{ct}</td><td>{ip}</td></tr>'
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


def _lines_to_list(text: str) -> list[str]:
    return [line.strip() for line in text.splitlines() if line.strip()]


def _sshkeys_to_text(keys) -> str:
    if not keys:
        return ""
    if isinstance(keys, str):
        return keys
    return "\n".join(keys)


def sanitize_disk(disk: dict) -> dict:
    out: dict = {"slot": disk["slot"], "type": disk["type"], "storage": disk["storage"]}
    if disk["type"] != "disk":
        return out
    if disk.get("size"):
        out["size"] = disk["size"]
    if disk.get("iothread"):
        out["iothread"] = True
    if disk.get("discard"):
        out["discard"] = True
    if disk.get("cache"):
        out["cache"] = disk["cache"]
    return out


def sanitize_ipconfig_entry(entry: dict) -> dict:
    out: dict = {}
    if entry.get("interface"):
        out["interface"] = entry["interface"]
    if entry.get("ip"):
        out["ip"] = entry["ip"]
    if entry.get("gateway"):
        out["gateway"] = entry["gateway"]
    return out


def sanitize_cloudinit(ci: dict) -> dict:
    out: dict = {"enabled": True}
    if ci.get("nameserver"):
        out["nameserver"] = ci["nameserver"]
    if ci.get("searchdomain"):
        out["searchdomain"] = ci["searchdomain"]
    keys = ci.get("sshkeys") or []
    if keys:
        out["sshkeys"] = keys
    ipconfig = [sanitize_ipconfig_entry(e) for e in ci.get("ipconfig", []) if e.get("ip")]
    if ipconfig:
        out["ipconfig"] = ipconfig
    return out


def sanitize_vm(vm: dict) -> dict:
    out: dict = {
        "name": vm["name"],
        "vmid": int(vm["vmid"]),
        "target_node": vm["target_node"],
        "clone": vm["clone"],
        "full_clone": bool(vm["full_clone"]),
    }
    if vm.get("onboot"):
        out["onboot"] = True
    tags = vm.get("tags") or []
    if tags:
        out["tags"] = tags
    out["cpu"] = {
        "cores": int(vm["cpu"]["cores"]),
        "sockets": int(vm["cpu"]["sockets"]),
        "type": vm["cpu"]["type"],
    }
    if vm.get("bios") == "ovmf":
        out["bios"] = "ovmf"
        out["machine"] = vm.get("machine", "q35")
        out["efi_storage"] = vm.get("efi_storage", "Internal")
    out["memory"] = int(vm["memory"])
    if vm.get("balloon") is not None:
        out["balloon"] = int(vm["balloon"])
    if vm.get("serial"):
        out["serial"] = {"id": int(vm["serial"]["id"]), "type": vm["serial"]["type"]}
    out["scsihw"] = vm["scsihw"]
    out["bootdisk"] = vm["bootdisk"]
    out["disks"] = [sanitize_disk(d) for d in vm.get("disks", [])]
    out["networks"] = [
        {
            "id": int(n["id"]),
            "model": n["model"],
            "bridge": n["bridge"],
            "firewall": bool(n.get("firewall", True)),
        }
        for n in vm.get("networks", [])
    ]
    ci = vm.get("cloudinit")
    if ci and ci.get("enabled"):
        out["cloudinit"] = sanitize_cloudinit(ci)
    agent = int(vm.get("agent", 0))
    if agent:
        out["agent"] = agent
    deps = vm.get("depends_on") or []
    if deps:
        out["depends_on"] = deps
    return out


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
    all_names = [v["name"] for v in vms]
    router_ips = get_router_ips()

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
                tags_text = st.text_input("Tags (comma-separated)", ", ".join(vm.get("tags", [])), key=f"tags_{i}")
                vm["tags"] = [t.strip() for t in tags_text.split(",") if t.strip()]
                vm["onboot"] = st.checkbox("On boot", value=vm.get("onboot", False), key=f"onboot_{i}")
            with col2:
                cpu = vm.get("cpu", {})
                cpu["cores"] = st.number_input("Cores", value=cpu.get("cores", 1), min_value=1, key=f"cores_{i}")
                cpu["sockets"] = st.number_input("Sockets", value=cpu.get("sockets", 1), min_value=1, key=f"sockets_{i}")
                cpu["type"] = st.text_input("CPU type", cpu.get("type", "host"), key=f"cpu_type_{i}")
                vm["cpu"] = cpu
                vm["memory"] = st.number_input("RAM (MB)", value=vm.get("memory", 1024), step=512, key=f"mem_{i}")
                vm["balloon"] = st.number_input("Balloon (MB)", value=vm.get("balloon", vm.get("memory", 1024)), step=512, key=f"balloon_{i}")
            with col3:
                vm["full_clone"] = st.selectbox(
                    "Clone", [True, False],
                    index=0 if vm.get("full_clone", True) else 1,
                    format_func=lambda x: "Full" if x else "Linked",
                    key=f"fc_{i}",
                )
                vm["scsihw"] = st.text_input("SCSI HW", vm.get("scsihw", "virtio-scsi-single"), key=f"scsihw_{i}")
                vm["bootdisk"] = st.text_input("Boot disk", vm.get("bootdisk", "scsi0"), key=f"bootdisk_{i}")
                vm["agent"] = 1 if st.checkbox(
                    "QEMU agent", value=bool(vm.get("agent", 0)), key=f"agent_{i}",
                ) else 0

            other_names = [n for j, n in enumerate(all_names) if j != i]
            deps = st.multiselect(
                "Depends on",
                options=other_names,
                default=[d for d in vm.get("depends_on", []) if d in other_names],
                key=f"deps_{i}",
            )
            if deps:
                vm["depends_on"] = deps
            else:
                vm.pop("depends_on", None)

            section("firmware & serial")
            fw1, fw2, fw3, fw4 = st.columns(4, vertical_alignment="bottom")
            with fw1:
                uefi = st.checkbox("UEFI (OVMF)", value=vm.get("bios") == "ovmf", key=f"uefi_{i}")
            if uefi:
                vm["bios"] = "ovmf"
                with fw2:
                    vm["machine"] = st.text_input("Machine", vm.get("machine", "q35"), key=f"machine_{i}")
                with fw3:
                    vm["efi_storage"] = st.text_input("EFI storage", vm.get("efi_storage", "Internal"), key=f"efi_{i}")
            else:
                vm.pop("bios", None)
                vm.pop("machine", None)
                vm.pop("efi_storage", None)

            has_serial = vm.get("serial") is not None
            with fw4:
                use_serial = st.checkbox("Serial console", value=has_serial, key=f"serial_en_{i}")
            if use_serial:
                serial = vm.get("serial", {"id": 0, "type": "socket"})
                s1, s2 = st.columns(2)
                with s1:
                    serial["id"] = st.number_input("Serial ID", value=serial.get("id", 0), min_value=0, key=f"serial_id_{i}")
                with s2:
                    serial["type"] = st.text_input("Serial type", serial.get("type", "socket"), key=f"serial_type_{i}")
                vm["serial"] = serial
            else:
                vm.pop("serial", None)

            section("disks")
            for di, disk in enumerate(vm.get("disks", [])):
                dc1, dc2, dc3, dc4, dc5, dc6, dc7 = st.columns(7, vertical_alignment="bottom")
                with dc1:
                    disk["slot"] = st.text_input("Slot", disk.get("slot", ""), key=f"disk_slot_{i}_{di}")
                with dc2:
                    disk["type"] = st.selectbox(
                        "Type", ["disk", "cloudinit"],
                        index=0 if disk.get("type", "disk") == "disk" else 1,
                        key=f"disk_type_{i}_{di}",
                    )
                with dc3:
                    disk["storage"] = st.text_input("Storage", disk.get("storage", ""), key=f"disk_storage_{i}_{di}")
                with dc4:
                    if disk["type"] == "disk":
                        disk["size"] = st.text_input("Size", disk.get("size", ""), key=f"disk_size_{i}_{di}")
                    else:
                        disk.pop("size", None)
                        disk.pop("cache", None)
                        disk.pop("iothread", None)
                        disk.pop("discard", None)
                with dc5:
                    if disk["type"] == "disk":
                        cache = disk.get("cache", "")
                        disk["cache"] = st.text_input("Cache", cache, key=f"disk_cache_{i}_{di}")
                        if not disk["cache"]:
                            disk.pop("cache", None)
                with dc6:
                    if disk["type"] == "disk":
                        disk["iothread"] = st.checkbox("IO thread", value=disk.get("iothread", False), key=f"disk_iothread_{i}_{di}")
                        if not disk["iothread"]:
                            disk.pop("iothread", None)
                with dc7:
                    if disk["type"] == "disk":
                        disk["discard"] = st.checkbox("Discard (TRIM)", value=disk.get("discard", False), key=f"disk_discard_{i}_{di}")
                        if not disk["discard"]:
                            disk.pop("discard", None)

            section("networks")
            for ni, net in enumerate(vm.get("networks", [])):
                nc1, nc2, nc3, nc4 = st.columns(4, vertical_alignment="bottom")
                with nc1:
                    net["id"] = st.number_input("Net ID", value=net.get("id", ni), min_value=0, key=f"net_id_{i}_{ni}")
                with nc2:
                    net["model"] = st.text_input("Model", net.get("model", "virtio"), key=f"net_model_{i}_{ni}")
                with nc3:
                    net["bridge"] = st.text_input("Bridge", net.get("bridge", "vmbr1"), key=f"net_bridge_{i}_{ni}")
                with nc4:
                    net["firewall"] = st.checkbox("Firewall", value=net.get("firewall", True), key=f"net_fw_{i}_{ni}")

            ci = vm.get("cloudinit", {})
            ci_enabled = st.checkbox("Cloud-init", value=ci.get("enabled", False), key=f"ci_en_{i}")
            if ci_enabled:
                ci["enabled"] = True
                section("cloud-init")
                c1, c2 = st.columns(2)
                with c1:
                    if not ci.get("ipconfig"):
                        ci["ipconfig"] = [{"interface": "net0", "ip": "", "gateway": ""}]
                    ci["ipconfig"][0]["interface"] = st.text_input(
                        "Interface", ci["ipconfig"][0].get("interface", "net0"), key=f"ci_iface_{i}",
                    )
                    ci["ipconfig"][0]["ip"] = st.text_input(
                        "IP/CIDR", ci["ipconfig"][0].get("ip", ""), key=f"ip_{i}",
                    )
                    ci["ipconfig"][0]["gateway"] = st.text_input(
                        "Gateway", ci["ipconfig"][0].get("gateway", ""), key=f"gw_{i}",
                    )
                with c2:
                    ns = st.text_input("DNS", ci.get("nameserver", ""), key=f"ns_{i}")
                    ci["nameserver"] = ns or None
                    if not ci["nameserver"]:
                        ci.pop("nameserver", None)
                    sd = st.text_input("Domain", ci.get("searchdomain", ""), key=f"sd_{i}")
                    ci["searchdomain"] = sd or None
                    if not ci["searchdomain"]:
                        ci.pop("searchdomain", None)
                ssh_text = st.text_area(
                    "SSH keys (one per line)",
                    value=_sshkeys_to_text(ci.get("sshkeys")),
                    key=f"sshkeys_{i}",
                    height=120,
                )
                keys = _lines_to_list(ssh_text)
                if keys:
                    ci["sshkeys"] = keys
                else:
                    ci.pop("sshkeys", None)
                gw = ci["ipconfig"][0].get("gateway", "")
                if not gw:
                    ci["ipconfig"][0].pop("gateway", None)
                vm["cloudinit"] = ci
            else:
                vm.pop("cloudinit", None)

            if vm["name"] == ROUTER_VM:
                section("router interfaces (template)")
                st.caption("Configured in pfSense template — stored locally, not in vms.json.")
                r1, r2 = st.columns(2)
                with r1:
                    router_ips["lan"] = st.text_input(
                        "LAN IP (vmbr1)", router_ips.get("lan", "172.16.10.1/24"), key=f"router_lan_{i}",
                    )
                with r2:
                    router_ips["wan"] = st.text_input(
                        "WAN IP (vmbr0)", router_ips.get("wan", ""), key=f"router_wan_{i}",
                        placeholder="e.g. dhcp or 203.0.113.1/24",
                    )

    if st.button("Save", type="primary", use_container_width=True):
        data["vms"] = [sanitize_vm(vm) for vm in vms]
        with open(vms_path, "w") as f:
            json.dump(data, f, indent=4)
        ui_cfg = read_ui_config()
        ui_cfg["router_ips"] = router_ips
        write_ui_config(ui_cfg)
        st.success("Saved")
        st.rerun()


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
    if sync_deploy_from_disk():
        clear_terminal_caches()
        st.rerun()
    status = read_deploy_status()
    text = read_deploy_log()
    state = status.get("state", "idle")
    footer = status.get("footer", "ready")
    render_terminal_cached(
        "deploy",
        st.empty(),
        text=text,
        state=state,
        footer=footer,
        term_id="deploy",
    )


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

    deploy_terminal = (
        st.fragment(run_every=timedelta(seconds=3))(_deploy_terminal_fragment)
        if job_running
        else st.fragment(_deploy_terminal_fragment)
    )
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


def _ansible_terminal_fragment():
    if sync_all_playbooks_from_disk():
        st.session_state.pop(f"term_cache_{ANSIBLE_TERMINAL_CACHE}", None)
    text, status, title = resolve_ansible_terminal()
    live = is_ansible_busy()
    render_terminal_cached(
        ANSIBLE_TERMINAL_CACHE,
        st.empty(),
        force=live,
        text=text,
        state=status.get("state", "idle"),
        footer=status.get("footer", "ready"),
        title=title,
        term_id="ansible",
    )


def _playbooks_tab():
    jobs_busy = is_ansible_busy()

    for i, (pb_file, pb_desc, color) in enumerate(PLAYBOOKS):
        key = playbook_job_key(pb_file)
        with st.container(border=True):
            card_col, status_col, run_col = st.columns([6, 1, 1], gap="small", vertical_alignment="center")
            state = playbook_run_state(pb_file)
            with card_col:
                st.markdown(
                    pb_card_html(i + 1, pb_desc, pb_file, color),
                    unsafe_allow_html=True,
                )
            with status_col:
                st.markdown(pb_state_html(state), unsafe_allow_html=True)
            with run_col:
                running = is_playbook_job_running(key)
                if running:
                    if st.button(
                        "Stop", key=f"stop_{pb_file}", type="primary", use_container_width=True,
                    ):
                        if stop_playbook_job(key):
                            st.rerun()
                else:
                    if st.button(
                        "Run", key=f"run_{pb_file}", type="primary", use_container_width=True,
                        disabled=jobs_busy,
                    ):
                        cmd = ansible_playbook_cmd(pb_file)
                        if start_playbook_job(
                            key, cmd, ANSIBLE_DIR,
                            f"{pb_desc} completed successfully",
                            f"{pb_desc} failed",
                            pb_file=pb_file,
                        ):
                            set_ansible_terminal_focus(key, f"cyberlab@ansible — {pb_file}")
                            st.rerun()
                        else:
                            st.warning("A playbook is already running.")


def _batch_playbooks_tab():
    batch_running = is_playbook_job_running(BATCH_PLAYBOOK_KEY)
    jobs_busy = is_ansible_busy()

    section("batch execution")
    clean_first = st.checkbox("Clear SSH keys before running", value=True)
    exclude = st.multiselect("Exclude", options=[d for _, d, _ in PLAYBOOKS])
    run_all = False
    if batch_running:
        if st.button("Stop", type="primary", key="batch_stop", use_container_width=True):
            if stop_playbook_job(BATCH_PLAYBOOK_KEY):
                st.rerun()
    else:
        run_all = st.button(
            "Execute All", type="primary", use_container_width=True,
            disabled=jobs_busy,
        )

    if not batch_running and run_all:
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

        parts = []
        if clean_first:
            parts.append(f'"{CLEAN_HOSTS_SCRIPT}"')
        for pb in pb_files:
            parts.append(f'echo "" && echo "=== {pb} ==="')
            parts.append(ansible_playbook_cmd(pb))
        batch_cmd = " && ".join(parts)
        if start_playbook_job(
            BATCH_PLAYBOOK_KEY, batch_cmd, ANSIBLE_DIR,
            "All playbooks complete", "Batch failed", running_label="batch",
        ):
            set_ansible_terminal_focus(BATCH_PLAYBOOK_KEY, "cyberlab@ansible — batch")
            st.rerun()
        else:
            st.warning("A playbook job is already running.")


def _ansible_stats_panel():
    render_playbook_stats()


def page_ansible():
    st.markdown(hero("Ansible"), unsafe_allow_html=True)
    st.markdown('<div class="hero-sub">Configure software & security stack</div>', unsafe_allow_html=True)

    if "playbook_outputs" not in st.session_state:
        st.session_state.playbook_outputs = {}
    if "playbook_status" not in st.session_state:
        st.session_state.playbook_status = {}

    sync_all_playbooks_from_disk()
    ansible_jobs_busy = is_ansible_busy()

    section("run summary")
    stats_panel = (
        st.fragment(run_every=timedelta(seconds=3))(_ansible_stats_panel)
        if ansible_jobs_busy
        else st.fragment(_ansible_stats_panel)
    )
    stats_panel()

    section("output")
    if ansible_jobs_busy:
        st.caption("Job running on server — safe to refresh or reconnect; output updates automatically.")
    ansible_terminal = (
        st.fragment(run_every=timedelta(seconds=3))(_ansible_terminal_fragment)
        if ansible_jobs_busy
        else st.fragment(_ansible_terminal_fragment)
    )
    ansible_terminal()

    section("ssh")
    st.caption("Clear stale SSH host keys before connecting to redeployed Linux VMs.")
    if st.button(
        "Clear SSH keys", key="ansible_clean_hosts",
        disabled=ansible_jobs_busy,
    ):
        if not file_exists(CLEAN_HOSTS_SCRIPT):
            st.error(f"Script not found: {CLEAN_HOSTS_SCRIPT}")
        else:
            os.chmod(CLEAN_HOSTS_SCRIPT, 0o755)
            if start_playbook_job(
                CLEAN_HOSTS_KEY,
                f'"{CLEAN_HOSTS_SCRIPT}"',
                BASE_DIR,
                "SSH keys cleared",
                "Failed to clear SSH keys",
                running_label="clean ssh keys",
            ):
                set_ansible_terminal_focus(CLEAN_HOSTS_KEY, "cyberlab@ansible — clean ssh keys")
                st.rerun()
            else:
                st.warning("Another job is already running.")

    tab1, tab2 = st.tabs(["Playbooks", "Run All"])

    with tab1:
        playbooks_tab = st.fragment(run_every=timedelta(seconds=3))(_playbooks_tab)
        playbooks_tab()

    with tab2:
        batch_tab = (
            st.fragment(run_every=timedelta(seconds=3))(_batch_playbooks_tab)
            if ansible_jobs_busy
            else st.fragment(_batch_playbooks_tab)
        )
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

_ = PAGES[page]()
