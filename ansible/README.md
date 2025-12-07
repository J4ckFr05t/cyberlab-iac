# Ansible Infrastructure Automation

## Directory Structure

```
ansible/
├── inventory/
│   └── hosts.ini              # Inventory file with host definitions
├── group_vars/
│   └── dc.yml                 # Variables for domain controller group
├── roles/
│   └── dc_setup/
│       └── tasks/
│           └── main.yml       # Domain controller setup tasks
├── playbooks/
│   └── dc_setup.yml           # Domain controller setup playbook
└── README.md                  # This file
```

## Domain Controller Setup

### Prerequisites

1. **Ansible Control Node:**
   - Ansible 2.9 or later
   - Python 3.6 or later
   - pywinrm package: `pip install pywinrm`
   - Required Ansible collections:
     ```bash
     ansible-galaxy collection install -r requirements.yml
     ```

2. **Target Windows Server:**
   - Windows Server 2016 or later
   - WinRM configured and accessible
   - Administrator credentials

### Configuration

The DC setup includes:
- Active Directory Domain Services installation
- Domain promotion (new forest: frostsec.corp)
- DNS Server configuration
- Organizational Units creation
- Domain users creation

### Credentials Setup

**Step 1: Create Ansible Vault file**

```bash
cd ansible
ansible-vault create group_vars/dc_vault.yml
```

You'll be prompted to create a vault password. Then add your credentials:

```yaml
---
# Windows Administrator Credentials
win_username: Administrator
win_password: YourWindowsAdminPassword

# Directory Services Restore Mode Password
dsrm_password: YourDSRMPassword

# Domain User Passwords
dave_password: DavePassword123!
sophia_password: SophiaPassword123!
```

**Step 2 (Optional): Create vault password file**

For automation, store the vault password in a file:

```bash
echo "your-vault-password" > .vault_pass
chmod 600 .vault_pass
```

> **Note:** The `.vault_pass` file is already in `.gitignore` to prevent accidental commits.

### Usage

**Option 1: Prompt for vault password**

```bash
ansible-playbook -i inventory/hosts.ini playbooks/dc_setup.yml --ask-vault-pass
```

**Option 2: Use vault password file**

```bash
ansible-playbook -i inventory/hosts.ini playbooks/dc_setup.yml --vault-password-file .vault_pass
```

### Managing Vault Files

**Edit encrypted vault:**
```bash
ansible-vault edit group_vars/dc_vault.yml
```

**View encrypted vault:**
```bash
ansible-vault view group_vars/dc_vault.yml
```

**Change vault password:**
```bash
ansible-vault rekey group_vars/dc_vault.yml
```

### Variables

**Stored in group_vars/dc_vault.yml (encrypted):**
- `win_username`: Windows administrator username
- `win_password`: Windows administrator password
- `dsrm_password`: Directory Services Restore Mode password
- `dave_password`: Password for dave.johnson user
- `sophia_password`: Password for sophia.davis user

**Configured in group_vars/dc.yml (plain text):**
- `domain_name`: frostsec.corp
- `domain_netbios_name`: FROSTSEC
- `organizational_units`: List of OUs to create
- `domain_users`: List of domain users to create

### Idempotency

All tasks are idempotent and safe to re-run:
- Features are only installed if not present
- Domain promotion only occurs if not already a DC
- OUs and users are created only if they don't exist
- DNS configuration is only changed if needed

### Tags

Use tags to run specific parts of the playbook:

```bash
# Only install features
ansible-playbook ... --tags install

# Only create users
ansible-playbook ... --tags users

# Only create OUs
ansible-playbook ... --tags ou

# Skip reboot
ansible-playbook ... --skip-tags reboot
```