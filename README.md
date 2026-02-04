# CyberLab Infrastructure as Code (IAC)

This project automates the deployment of a complete cybersecurity lab using **Terraform** (Infrastructure provisioning) and **Ansible** (Configuration Management) on Proxmox VE.

## Project Structure

- **[`terraform/`](terraform/README.md)**: Proxmox VM provisioning (VMs, Networking, CloudInit).
- **[`ansible/`](ansible/README.md)**: Configuration of Domain Controllers, DNS, ELK Stack (SIEM), Fleet, and Wazuh.
- **`scripts/`**: Utility scripts for maintenance and setup.

## Quick Start

### 1. Prerequisites
- A running Proxmox VE server.
- Terraform and Ansible installed on your control machine.
- Local VM templates created in Proxmox (see [`terraform/README.md`](terraform/README.md#prerequisites)).

### 2. Infrastructure Layer (Terraform)
Provision the virtual machines.

1. Navigate to `terraform/`.
2. Configure `terraform.tfvars`.
3. Run `terraform init` and `terraform apply`.
4. Run the post-deployment script to fix EFI disks for Windows VMs (see usage guide).

👉 **[Detailed Terraform Instructions](terraform/README.md)**

### 3. Configuration Layer (Ansible)
Configure services and security tools.

1. Navigate to `ansible/`.
2. Set up `secret_vault.yml` with your credentials.
3. Run the playbooks in the following **strict order**:

    1.  **DC Setup** (`dc_setup.yml`)
    2.  **Configure DNS** (`configure_dns.yml`)
    3.  **Join Domain** (`join_to_domain.yml`)
    4.  **ELK & Fleet Setup** (`siem_stack.yml`)
    5.  **Enroll Elastic Agents** (`enroll_elastic_agents.yml`)
    6.  **Setup Wazuh** (`setup_wazuh.yml`)
    7.  **Enroll Wazuh Agents** (`enroll_wazuh_agents.yml`)
    8.  **Setup TheHive** (`setup_thehive.yml`)
    9.  **Wazuh-TheHive Integration** (`wazuh_thehive_integration.yml`)
    10. **Setup Suricata** (`suricata_setup.yml`)

👉 **[Detailed Ansible Instructions](ansible/README.md)**

## Architecture Overview

The lab consists of:
- **Router**: pfSense (Gateway)
- **Identity**: Windows Server 2022 (Domain Controller)
- **SIEM**: ELK Stack + Fleet Server (Ubuntu)
- **XDR**: Wazuh Manager (Ubuntu)
- **Endpoints**: Windows 11 & Ubuntu Desktop workstations