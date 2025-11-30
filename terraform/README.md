# Proxmox Terraform Infrastructure

This directory contains the Terraform configuration for managing Proxmox Virtual Machines using a data-driven approach. Instead of defining resources manually in HCL, VMs are defined in a JSON file, making it easier to manage and version control your infrastructure.

## Structure

- **`vms.json`**: The source of truth for VM definitions. Contains hardware specs, network config, and CloudInit settings.
- **`main.tf`**: The Terraform logic that reads `vms.json` and dynamically creates `proxmox_vm_qemu` resources.
- **`variables.tf`**: Input variable declarations.
- **`providers.tf`**: Proxmox provider configuration.
- **`terraform.tfvars`**: (Git-ignored) Local secrets and configuration values.

## Prerequisites

1.  **Terraform**: Ensure Terraform is installed on your machine.
2.  **Proxmox User**: A Proxmox user with appropriate permissions and an API Token.

## Setup

1.  Initialize Terraform:
    ```bash
    terraform init
    ```

2.  Configure Secrets:
    Copy the example variables file:
    ```bash
    cp terraform.tfvars.example terraform.tfvars
    ```
    Edit `terraform.tfvars` and fill in your Proxmox details:
    - `proxmox_api_url`: Your Proxmox API endpoint.
    - `proxmox_api_token_id`: Your API Token ID (e.g., `user@pam!token`).
    - `proxmox_api_token_secret`: Your API Token Secret.
    - `vm_passwords`: A map of passwords for your VMs (if using CloudInit).

## Usage

### Adding a New VM

1.  Open `vms.json`.
2.  Add a new entry to the `vms` list. You can copy an existing object as a template.
    ```json
    {
      "name": "new-vm-name",
      "target_node": "proxmox",
      "clone": "template-name",
      "full_clone": true,
      "cpu": { ... },
      "memory": 2048,
      ...
    }
    ```
3.  If the VM uses CloudInit and requires a password, add it to `terraform.tfvars`:
    ```hcl
    vm_passwords = {
      "new-vm-name" = "secret-password"
    }
    ```

### Deploying

1.  **Plan**: Preview changes.
    ```bash
    terraform plan
    ```
2.  **Apply**: Create or update VMs.
    ```bash
    terraform apply
    ```

## Advanced Details

### Lifecycle Management
The `main.tf` splits VMs into two groups based on the `ignore_network_changes` flag in `vms.json`:
- **`true`**: Terraform will ignore changes to the network configuration after creation. Useful for guests that modify their own interfaces.
- **`false`** (default): Terraform will enforce the network state defined in JSON.

### CloudInit
CloudInit settings (IP, Gateway, User) are automatically configured if `cloudinit.enabled` is set to `true` in the JSON. The drive is automatically added to the VM configuration.
