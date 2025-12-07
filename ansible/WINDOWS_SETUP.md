# Windows Credentials Setup - Quick Guide

## Problem
```
fatal: [win-01-ws]: UNREACHABLE! => {"changed": false, "msg": "ntlm: auth method ntlm requires a username", "unreachable": true}
```

This error occurs because Ansible needs credentials to connect to Windows hosts via WinRM.

## Solution

### Step 1: Create the Windows Vault File

Run this command from the `ansible` directory:

```bash
cd ~/cyberlab-iac/ansible
ansible-vault create group_vars/windows_vault.yml
```

You'll be prompted to:
1. Enter a vault password (use the same one as your DC vault for simplicity)
2. An editor will open

### Step 2: Add Your Windows Credentials

In the editor, add:

```yaml
---
# Windows Local Administrator Credentials
win_username: Administrator
win_password: YourActualWindowsPassword
```

Replace `YourActualWindowsPassword` with the actual Administrator password for your Windows workstations.

Save and exit the editor (`:wq` in vim, or `Ctrl+X` then `Y` in nano).

### Step 3: Run the Playbook

**Option 1: With vault password prompt**
```bash
ansible-playbook -i inventory/hosts.ini playbooks/configure_dns.yml --limit win-01-ws --ask-vault-pass
```

**Option 2: With vault password file (if you have .vault_pass)**
```bash
ansible-playbook -i inventory/hosts.ini playbooks/configure_dns.yml --limit win-01-ws --vault-password-file .vault_pass
```

## What Was Created

1. **`group_vars/windows.yml`** - WinRM configuration for Windows hosts
   - Sets up WinRM connection
   - References vault credentials
   - Configures NTLM authentication

2. **`group_vars/windows_vault.yml.example`** - Example vault file
   - Shows the format for credentials
   - Not encrypted (just an example)

3. **`group_vars/windows_vault.yml`** - You need to create this (encrypted)
   - Contains actual credentials
   - Encrypted with ansible-vault

## Verify Setup

After creating the vault, verify the files exist:

```bash
ls -la group_vars/
```

You should see:
- `windows.yml` (plain text - WinRM config)
- `windows_vault.yml` (encrypted - credentials)
- `windows_vault.yml.example` (plain text - example)

## Test Connection

Test if Ansible can connect to Windows hosts:

```bash
ansible windows -i inventory/hosts.ini -m win_ping --ask-vault-pass
```

Expected output:
```
win-01-ws | SUCCESS => {
    "changed": false,
    "ping": "pong"
}
```

## Troubleshooting

### Wrong Password
If you get authentication errors, edit the vault:
```bash
ansible-vault edit group_vars/windows_vault.yml
```

### Forgot Vault Password
You'll need to recreate the vault file:
```bash
rm group_vars/windows_vault.yml
ansible-vault create group_vars/windows_vault.yml
```

### WinRM Not Configured on Windows Host
Ensure WinRM is enabled on the Windows machine:
```powershell
# On the Windows host
winrm quickconfig
winrm set winrm/config/service/auth '@{Basic="true"}'
winrm set winrm/config/service '@{AllowUnencrypted="true"}'
```

## Security Notes

- The `windows_vault.yml` file is encrypted and safe to commit to git
- The `.vault_pass` file is in `.gitignore` - never commit it
- Use strong passwords for both Windows and vault
- Consider using different credentials for workstations vs servers
