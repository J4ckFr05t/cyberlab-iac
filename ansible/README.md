# Ansible Infrastructure Automation

## Directory Structure

```
ansible/
├── inventory/
│   ├── hosts.ini              # Inventory file with host definitions
│   └── group_vars/            # Group variables
│       ├── all.yml            # Global variables
│       ├── dc.yml             # Domain Controller variables
│       ├── linux.yml          # Linux specific variables
│       ├── windows.yml        # Windows specific variables
│       └── secret_vault.yml   # Encrypted secrets (Ansible Vault)
├── roles/                     # Ansible roles (dc_setup, linux_join_domain, etc.)
├── playbooks/
│   ├── dc_setup.yml           # Domain controller setup
│   ├── configure_dns.yml      # DNS configuration
│   ├── join_to_domain.yml     # Domain join for Windows/Linux
│   ├── siem_stack.yml         # ELK and Fleet setup
│   └── check_connectivity.yml # Connectivity test
└── README.md                  # This file
```

## Prerequisites

1. **Ansible Control Node:**
   - Ansible 2.9 or later
   - Python 3.6 or later
   - `pip install pywinrm`
   - Required Collections: `ansible-galaxy collection install -r requirements.yml`

2. **Target Hosts:**
   - **Windows**: WinRM configured, Administrator credentials.
   - **Linux**: SSH access, sudo privileges.

## Credentials Setup

We use a **single consolidated vault file** (`secret_vault.yml`) for all sensitive credentials.

### 1. Create/Edit Vault

```bash
ansible-vault create inventory/group_vars/secret_vault.yml
# OR to edit existing:
ansible-vault edit inventory/group_vars/secret_vault.yml
```

### 2. Required Secrets Structure

Add your credentials to `secret_vault.yml`:

```yaml
---
# Windows/AD Administrator
win_username: Administrator
win_password: YourDeviceAdminPassword

# Domain Recovery
dsrm_password: YourDSRMPassword

# User Passwords
dave_password: UserPassword1!
sophia_password: UserPassword2!

# ELK Stack
elastic_custom_password: YourElasticPassword
```

### 3. Vault Password File

Store your vault password in `.vault_pass` (this file is git-ignored):

```bash
echo "your-vault-password" > .vault_pass
chmod 600 .vault_pass
```

## Playbooks

### 1. Domain Controller Setup (`dc_setup.yml`)

Promotes the Windows Server to a Domain Controller for `frostsec.corp`.

```bash
ansible-playbook -i inventory/hosts.ini playbooks/dc_setup.yml
```

**Configuration (`inventory/group_vars/dc.yml`):**

```yaml
domain_users:
  - display_name: Dave Johnson
    firstname: Dave
    lastname: Johnson
    password: "{{ dave_password }}" # References vault
    ...
```

### 2. DNS Configuration (`configure_dns.yml`)

Configures all hosts (Linux & Windows) to use the DC (`172.16.10.100`) as their primary DNS server. Critical for domain joining.

```bash
ansible-playbook -i inventory/hosts.ini playbooks/configure_dns.yml
```

### 3. Domain Join (`join_to_domain.yml`)

Joins Linux and Windows workstations to the `frostsec.corp` domain.

**Features:**
- **Linux**: Uses `realm` and `sssd` for AD integration.
- **Windows**: Uses `microsoft.ad.domain` module.
- **Note**: Ensure DNS is configured correctly before running this!

```bash
# Join all eligible hosts
ansible-playbook -i inventory/hosts.ini playbooks/join_to_domain.yml

# Join only Windows hosts
ansible-playbook -i inventory/hosts.ini playbooks/join_to_domain.yml --limit windows
```

### 4. SIEM Stack Deployment (`siem_stack.yml`)

Deploys the Elastic Stack (ELK) and Fleet Server.

**Components:**
- **SIEM-01-SRV**: Elasticsearch, Kibana, Logstash
- **FLEET-01-SRV**: Elastic Fleet Server

```bash
ansible-playbook -i inventory/hosts.ini playbooks/siem_stack.yml
```

## Troubleshooting

- **WinRM Failures**: Verify `ansible_user` and `ansible_password` in `secret_vault.yml` match the local admin credentials of the template.
- **DNS Resolution**: If domain join fails, run `configure_dns.yml` again and verify `nslookup frostsec.corp` returns the DC's IP.
- **Vault Errors**: Ensure `.vault_pass` exists and contains the correct password.

## Workflow

1. **Deploy Infrastructure** (Terraform).
2. **Setup DC**: `ansible-playbook playbooks/dc_setup.yml`
3. **Configure DNS**: `ansible-playbook playbooks/configure_dns.yml`
4. **Join Domain**: `ansible-playbook playbooks/join_to_domain.yml`
5. **Deploy SIEM**: `ansible-playbook playbooks/siem_stack.yml`