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
├── files/                     # Static files (packages, scripts, etc.)
├── roles/                     # Ansible roles (dc_setup, elk_setup, wazuh_server_setup, etc.)
├── playbooks/
│   ├── dc_setup.yml             # Domain controller setup
│   ├── configure_dns.yml        # DNS configuration
│   ├── join_to_domain.yml       # Domain join for Windows/Linux
│   ├── siem_stack.yml           # ELK and Fleet setup
│   ├── enroll_elastic_agents.yml# Elastic Agent enrollment
│   ├── setup_wazuh.yml          # Wazuh Manager setup
│   ├── enroll_wazuh_agents.yml  # Wazuh Agent enrollment
│   ├── setup_thehive.yml        # TheHive Setup & SOC Manager config
│   ├── wazuh_thehive_integration.yml # Wazuh-TheHive Integration
│   └── check_connectivity.yml   # Connectivity test
└── README.md                    # This file
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

# Wazuh
wazuh_api_password: YourWazuhApiPassword
wazuh_admin_password: YourWazuhAdminPassword
```

### 3. Vault Password File

Store your vault password in `.vault_pass` (this file is git-ignored):

```bash
echo "your-vault-password" > .vault_pass
chmod 600 .vault_pass
```

## Workflow (Strict Order)

Follow this order exactly for a successful deployment.

### 1. Domain Controller Setup (`dc_setup.yml`)
Promotes the Windows Server to a Domain Controller for `frostsec.corp`.

```bash
ansible-playbook -i inventory/hosts.ini playbooks/dc_setup.yml
```

### 2. Configure DNS (`configure_dns.yml`)
Configures all hosts (Linux & Windows) to use the DC (`172.16.10.100`) as their primary DNS server. Critical for domain joining.

```bash
ansible-playbook -i inventory/hosts.ini playbooks/configure_dns.yml
```

### 3. Join Domain (`join_to_domain.yml`)
Joins Linux and Windows workstations to the `frostsec.corp` domain.

```bash
ansible-playbook -i inventory/hosts.ini playbooks/join_to_domain.yml
```

### 4. ELK & Fleet Setup (`siem_stack.yml`)
Deploys the Elastic Stack (Elasticsearch, Kibana, Logstash) on `SIEM-01-SRV` and Fleet Server on `FLEET-01-SRV`.

```bash
ansible-playbook -i inventory/hosts.ini playbooks/siem_stack.yml
```

### 5. Enroll Elastic Agents (`enroll_elastic_agents.yml`)
Installs Elastic Agent on endpoints and enrolls them into Fleet.

```bash
ansible-playbook -i inventory/hosts.ini playbooks/enroll_elastic_agents.yml
```

### 6. Setup Wazuh (`setup_wazuh.yml`)
Deploys the Wazuh Manager on `XDR-01-SRV`.

```bash
ansible-playbook -i inventory/hosts.ini playbooks/setup_wazuh.yml
```

### 7. Enroll Wazuh Agents (`enroll_wazuh_agents.yml`)
Installs Wazuh Agent on endpoints and enrolls them with the Wazuh Manager.

```bash
ansible-playbook -i inventory/hosts.ini playbooks/enroll_wazuh_agents.yml
```

### 8. Setup TheHive (`setup_thehive.yml`)
Deploys TheHive, creates the "FrostSec Corp" organization, and the SOC Manager user/API Key.

```bash
ansible-playbook -i inventory/hosts.ini playbooks/setup_thehive.yml
```

### 9. Wazuh-TheHive Integration (`wazuh_thehive_integration.yml`)
Configures Wazuh to send alerts to TheHive using the `custom-w2thive` script.

```bash
ansible-playbook -i inventory/hosts.ini playbooks/wazuh_thehive_integration.yml
```

## Troubleshooting

- **WinRM Failures**: Verify `ansible_user` and `ansible_password` in `secret_vault.yml` match the local admin credentials of the template.
- **DNS Resolution**: If domain join fails, run `configure_dns.yml` again and verify `nslookup frostsec.corp` returns the DC's IP.
- **Vault Errors**: Ensure `.vault_pass` exists and contains the correct password.
- **Agent Enrollment Errors**: Ensure the Fleet Server or Wazuh Manager is reachable from the endpoints on the correct ports (8220 for Fleet, 1514/1515 for Wazuh).