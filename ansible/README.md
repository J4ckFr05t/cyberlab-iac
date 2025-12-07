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
│   ├── dc_setup.yml           # Domain controller setup playbook
│   └── configure_dns.yml      # DNS configuration playbook
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
- DNS Server configuration with forwarders
- Reverse DNS lookup zone creation
- PTR record for Domain Controller
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

---

## DNS Configuration

### Overview

The DNS configuration playbook (`configure_dns.yml`) sets up all hosts (except pfSense and DC) to use the Domain Controller as their primary DNS server.

### Features

- ✅ Automatically retrieves DC IP from inventory
- ✅ Supports Windows hosts (using `win_dns_client`)
- ✅ Supports Linux hosts with both systemd-resolved and traditional `/etc/resolv.conf`
- ✅ Excludes pfSense and DC hosts automatically
- ✅ Idempotent - safe to run multiple times
- ✅ Includes DNS verification tests

### Prerequisites

**Windows Hosts:**
- WinRM configured and accessible
- PowerShell 3.0 or higher
- Administrator privileges

**Linux Hosts:**
- SSH access configured
- sudo privileges
- Python installed

**Ansible Collections:**
```bash
ansible-galaxy collection install -r requirements.yml
```

### Usage

**Run the playbook:**
```bash
ansible-playbook -i inventory/hosts.ini playbooks/configure_dns.yml
```

**Run for specific host groups:**
```bash
# Only Windows hosts
ansible-playbook -i inventory/hosts.ini playbooks/configure_dns.yml --limit windows

# Only Linux hosts
ansible-playbook -i inventory/hosts.ini playbooks/configure_dns.yml --limit linux,infra

# Specific host
ansible-playbook -i inventory/hosts.ini playbooks/configure_dns.yml --limit win-01-ws
```

**Dry run (check mode):**
```bash
ansible-playbook -i inventory/hosts.ini playbooks/configure_dns.yml --check
```

### What It Does

**For Windows hosts:**
1. Retrieves the DC IP address from inventory (`172.16.10.100`)
2. Identifies the active network adapter
3. Configures the DNS server using `win_dns_client` module
4. Reports success/failure

**For Linux hosts:**

The playbook automatically detects the DNS management method:

- **If systemd-resolved is active** (Ubuntu 18.04+, Debian 10+):
  - Creates `/etc/systemd/resolved.conf.d/dns.conf`
  - Sets DNS to DC IP
  - Configures search domain as `frostsec.corp`
  - Restarts systemd-resolved service
  - Ensures `/etc/resolv.conf` is properly symlinked

- **If traditional resolv.conf is used:**
  - Backs up existing `/etc/resolv.conf` to `/etc/resolv.conf.backup`
  - Creates new `/etc/resolv.conf` with DC DNS
  - Sets search domain as `frostsec.corp`
  - Makes file immutable to prevent NetworkManager from overwriting

### Excluded Hosts

The following hosts are **automatically excluded** by targeting specific groups:
- **pfSense** - Not in any targeted group
- **DC (dc-01-srv)** - In `[dc]` group which is not targeted

### Verification

Test DNS resolution manually:

**Windows:**
```powershell
nslookup dc-01-srv.frostsec.corp
Get-DnsClientServerAddress
```

**Linux:**
```bash
nslookup dc-01-srv.frostsec.corp
cat /etc/resolv.conf
systemd-resolve --status  # For systemd-resolved systems
```

### Troubleshooting

**Windows Issues:**
- **WinRM connection failed**: Ensure WinRM is configured and firewall allows ports 5985/5986
- **Access denied**: Verify the Ansible user has Administrator privileges

**Linux Issues:**
- **Permission denied**: Ensure `ansible_become=true` is set and user has sudo privileges
- **DNS not persisting**: Check if NetworkManager is overwriting settings. Consider configuring NetworkManager directly:
  ```bash
  nmcli connection modify <connection-name> ipv4.dns "172.16.10.100"
  nmcli connection modify <connection-name> ipv4.ignore-auto-dns yes
  ```

---

## Typical Workflow

1. **Deploy VMs** using Terraform (see `../terraform/`)
2. **Setup Domain Controller** using `dc_setup.yml`
3. **Configure DNS** on all hosts using `configure_dns.yml`
4. **Join hosts to domain** (future playbook)