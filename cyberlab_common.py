"""Shared helpers for cyberlab.py and cyberlab_ui.py."""

DEFAULT_ANSIBLE_INVENTORY = "inventory/hosts.ini"


def ansible_playbook_cmd(playbook_name: str, inventory_file: str = DEFAULT_ANSIBLE_INVENTORY) -> str:
    """Build the ansible-playbook command used by both CLI and UI."""
    return f"ansible-playbook -i {inventory_file} playbooks/{playbook_name}"
