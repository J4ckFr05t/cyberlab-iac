# Proxmox Terraform Infrastructure

This directory contains the Terraform configuration for managing Proxmox Virtual Machines using a data-driven approach. Instead of defining resources manually in HCL, VMs are defined in a JSON file (`vms.json`), making it easier to manage and version control your infrastructure.

## Structure

- **[`vms.json`](file:///Users/jibingeorge/Documents/cyberlab-iac/terraform/vms.json)**: The source of truth for VM definitions. Contains hardware specs, network config, and CloudInit settings.
- **[`main.tf`](file:///Users/jibingeorge/Documents/cyberlab-iac/terraform/main.tf)**: The Terraform logic that reads `vms.json` and dynamically creates `proxmox_vm_qemu` resources.
- **[`variables.tf`](file:///Users/jibingeorge/Documents/cyberlab-iac/terraform/variables.tf)**: Input variable declarations.
- **[`providers.tf`](file:///Users/jibingeorge/Documents/cyberlab-iac/terraform/providers.tf)**: Proxmox provider configuration (using telmate/proxmox v3.0.2-rc05).
- **`terraform.tfvars`**: (Git-ignored) Local secrets and configuration values.
- **`terraform.tfvars.example`**: Example configuration file with placeholders.

## Prerequisites

1. **Terraform**: Ensure Terraform is installed on your machine.
2. **Proxmox User**: A Proxmox user with appropriate permissions and an API Token.
3. **VM Templates**: Pre-configured VM templates in Proxmox (e.g., `ubuntu-server-template`, `win11-template`, `pfsense-template`).

## Setup

1. **Initialize Terraform**:
   ```bash
   terraform init
   ```

2. **Configure Secrets**:
   Copy the example variables file:
   ```bash
   cp terraform.tfvars.example terraform.tfvars
   ```
   
   Edit `terraform.tfvars` and fill in your Proxmox details:
   ```hcl
   proxmox_api_url          = "https://your-proxmox-server:8006/api2/json"
   proxmox_api_token_id     = "your-token-id@pam!your-token-name"
   proxmox_api_token_secret = "your-secret-token"
   
   # Template-based passwords (shared by all VMs using the same template)
   template_passwords = {
     "ubuntu-server-template"  = "your-ubuntu-password"
     "ubuntu-desktop-template" = "your-ubuntu-desktop-password"
     "win11-template"          = "your-windows-password"
     "win-dc-2022-template"    = "your-windows-dc-password"
   }
   ```

## Usage

### Adding a New VM

1. Open `vms.json`.
2. Add a new entry to the `vms` array. See the [VM Configuration Schema](#vm-configuration-schema) section below for all available options.
3. If the VM uses CloudInit, ensure the template password is configured in `terraform.tfvars`.

### Deploying

1. **Plan**: Preview changes before applying.
   ```bash
   terraform plan
   ```

2. **Apply**: Create or update VMs.
   ```bash
   terraform apply
   ```

3. **Post-Deployment (In Proxmox Host Shell): Fix EFI Disk Format for Windows VMs** (Required for Snapshots)
   
   > [!IMPORTANT]
   > After `terraform apply` completes, you must manually fix the EFI disk format for UEFI-based Windows VMs. Terraform creates EFI disks in `raw` format by default, which **does not support snapshots**. This script converts them to `qcow2` format.
   
   Run this script on your Proxmox host:
   ```bash
   #!/bin/bash
   # Fix EFI disk format for UEFI VMs
   
   echo "Fixing EFI disk format for DC-01-SRV (VMID 201)..."
   qm stop 201
   qm set 201 -delete efidisk0
   qm set 201 -efidisk0 Internal:0,format=qcow2,efitype=4m,pre-enrolled-keys=1
   qm start 201
   
   echo "Fixing EFI disk format for WIN-01-WS (VMID 206)..."
   qm stop 206
   qm set 206 -delete efidisk0
   qm set 206 -efidisk0 Internal:0,format=qcow2,efitype=4m,pre-enrolled-keys=1
   qm start 206
   
   echo "Done! EFI disks are now in qcow2 format. Snapshots are now supported."
   ```
   
   **What this does:**
   - Stops each Windows VM
   - Deletes the existing `raw` format EFI disk
   - Recreates the EFI disk in `qcow2` format with the same settings
   - Restarts the VM
   
   **Note**: Adjust the script if you add more UEFI-based VMs (those with `"bios": "ovmf"`).

4. **Destroy**: Remove specific VMs or all infrastructure.
   ```bash
   terraform destroy
   ```

## Key Features

### 1. VM Dependency Management

The configuration automatically handles VM dependencies using the `depends_on` field in `vms.json`:

- **Independent VMs**: VMs without dependencies (e.g., `PF-01-RTR` router) are created in parallel.
- **Dependent VMs**: VMs that depend on other VMs (e.g., servers depending on the router) wait for their dependencies to be created first.

Example:
```json
{
  "name": "DC-01-SRV",
  "depends_on": ["PF-01-RTR"]
}
```

### 2. Template-Based Authentication

Authentication is managed at the **template level**, not per VM:

- Each template has a default username defined in `main.tf` (e.g., `sysadmin` for Ubuntu, `Administrator` for Windows).
- Passwords are configured per template in `terraform.tfvars` using the `template_passwords` map.
- All VMs cloned from the same template share the same credentials.

### 3. Disk Optimization for SSD Storage

All VM disks are optimized for SSD performance:

- **Format**: `qcow2` (supports snapshots, unlike raw format)
- **Discard**: Enabled (`discard: true`) for TRIM support
- **Cache**: `writeback` for optimal performance
- **IOThread**: Enabled for high-performance disks

Example disk configuration:
```json
{
  "slot": "scsi0",
  "size": "64G",
  "type": "disk",
  "storage": "Internal",
  "iothread": true,
  "format": "qcow2",
  "discard": true,
  "cache": "writeback"
}
```

### 4. UEFI/BIOS Support

The configuration supports both legacy BIOS and UEFI boot:

- **BIOS VMs**: Use `"bios": "seabios"` (default)
- **UEFI VMs**: Use `"bios": "ovmf"` with automatic EFI disk creation
  - Requires `"machine": "q35"` for modern hardware emulation
  - EFI disk is automatically created with `efitype: "4m"` and pre-enrolled keys

### 5. CloudInit Integration

CloudInit is fully supported for automated VM provisioning:

- Static IP configuration with gateway
- Multiple network interfaces (ipconfig0, ipconfig1)
- SSH key injection
- DNS server configuration
- Template-based user credentials

### 6. VM Tagging

VMs can be tagged for organization (e.g., `"tags": ["Lab"]`). Tags are automatically joined with semicolons when applied to Proxmox.

### 7. Serial Console Support

Windows VMs can have serial console enabled for troubleshooting:
```json
"serial": {
  "id": 0,
  "type": "socket"
}
```

## VM Configuration Schema

Below is the complete schema for VM definitions in `vms.json`:

```json
{
  "vms": [
    {
      "name": "VM-NAME",                    // Required: Unique VM name
      "vmid": 200,                          // Required: Unique VM ID
      "target_node": "proxmox",             // Required: Proxmox node name
      "clone": "template-name",             // Required: Template to clone from
      "full_clone": true,                   // Required: Full clone vs linked clone
      "onboot": true,                       // Optional: Start VM on host boot (default: false)
      "tags": ["Lab"],                      // Optional: Array of tags
      
      "cpu": {                              // Required: CPU configuration
        "cores": 2,
        "sockets": 1,
        "type": "host"                      // "host" for best performance
      },
      
      "memory": 4096,                       // Required: RAM in MB
      "scsihw": "virtio-scsi-single",       // Required: SCSI controller type
      "bootdisk": "scsi0",                  // Required: Boot disk identifier
      "agent": 1,                           // Optional: QEMU guest agent (0 or 1)
      
      "bios": "ovmf",                       // Optional: "seabios" (default) or "ovmf" (UEFI)
      "machine": "q35",                     // Optional: Machine type (required for UEFI)
      "efi_storage": "Internal",            // Optional: Storage for EFI disk (required if bios=ovmf)
      
      "serial": {                           // Optional: Serial console
        "id": 0,
        "type": "socket"
      },
      
      "disks": [                            // Required: Array of disks
        {
          "slot": "scsi0",                  // Required: Disk slot
          "size": "64G",                    // Optional: Disk size (omit if not resizing)
          "type": "disk",                   // Required: "disk" or "cloudinit"
          "storage": "Internal",            // Required: Storage pool name
          "iothread": true,                 // Optional: Enable IOThread (default: false)
          "format": "qcow2",                // Optional: Disk format (default: qcow2)
          "discard": true,                  // Optional: Enable TRIM (default: null)
          "cache": "writeback"              // Optional: Cache mode (default: null)
        },
        {
          "slot": "ide2",                   // CloudInit drive
          "type": "cloudinit",
          "storage": "local"
        }
      ],
      
      "networks": [                         // Required: Array of network interfaces
        {
          "id": 0,                          // Required: Network interface ID
          "model": "virtio",                // Required: Network adapter model
          "bridge": "vmbr1",                // Required: Bridge name
          "firewall": true                  // Required: Enable firewall
        }
      ],
      
      "cloudinit": {                        // Optional: CloudInit configuration
        "enabled": true,                    // Required if cloudinit block present
        "sshkeys": "ssh-rsa AAAA...",       // Optional: SSH public key
        "nameserver": "8.8.8.8",            // Optional: DNS server
        "ipconfig": [                       // Optional: Static IP configuration
          {
            "interface": "net0",            // Interface name (informational)
            "ip": "172.16.10.100/24",       // IP address with CIDR
            "gateway": "172.16.10.1"        // Optional: Default gateway
          }
        ]
      },
      
      "depends_on": ["PF-01-RTR"]           // Optional: Array of VM names to depend on
    }
  ]
}
```

## Example VM Configurations

### pfSense Router (BIOS, No CloudInit)
```json
{
  "name": "PF-01-RTR",
  "vmid": 200,
  "target_node": "proxmox",
  "clone": "pfsense-template",
  "full_clone": true,
  "onboot": true,
  "tags": ["Lab"],
  "cpu": {"cores": 1, "sockets": 1, "type": "host"},
  "memory": 2048,
  "scsihw": "virtio-scsi-single",
  "bootdisk": "scsi0",
  "disks": [
    {
      "slot": "scsi0",
      "size": "32G",
      "type": "disk",
      "storage": "Internal",
      "iothread": true,
      "format": "qcow2",
      "discard": true,
      "cache": "writeback"
    }
  ],
  "networks": [
    {"id": 0, "model": "virtio", "bridge": "vmbr0", "firewall": true},
    {"id": 1, "model": "virtio", "bridge": "vmbr1", "firewall": true}
  ]
}
```

### Ubuntu Server (BIOS, CloudInit)
```json
{
  "name": "SIEM-01-SRV",
  "vmid": 202,
  "target_node": "proxmox",
  "clone": "ubuntu-server-template",
  "full_clone": true,
  "onboot": true,
  "tags": ["Lab"],
  "cpu": {"cores": 2, "sockets": 1, "type": "host"},
  "memory": 4096,
  "serial": {"id": 0, "type": "socket"},
  "scsihw": "virtio-scsi-pci",
  "bootdisk": "scsi0",
  "disks": [
    {
      "slot": "scsi0",
      "size": "150G",
      "type": "disk",
      "storage": "Internal",
      "format": "qcow2",
      "discard": true,
      "cache": "writeback"
    },
    {"slot": "ide2", "type": "cloudinit", "storage": "local"}
  ],
  "networks": [
    {"id": 0, "model": "virtio", "bridge": "vmbr1", "firewall": true}
  ],
  "cloudinit": {
    "enabled": true,
    "sshkeys": "ssh-rsa AAAA...",
    "ipconfig": [
      {"interface": "net0", "ip": "172.16.10.210/24", "gateway": "172.16.10.1"}
    ]
  },
  "agent": 1,
  "depends_on": ["PF-01-RTR"]
}
```


### Windows Server (UEFI, CloudInit)
```json
{
  "name": "DC-01-SRV",
  "vmid": 201,
  "target_node": "proxmox",
  "clone": "win-dc-2022-template",
  "full_clone": true,
  "onboot": true,
  "tags": ["Lab"],
  "cpu": {"cores": 2, "sockets": 1, "type": "host"},
  "bios": "ovmf",
  "machine": "q35",
  "efi_storage": "Internal",
  "memory": 2048,
  "serial": {"id": 0, "type": "socket"},
  "scsihw": "virtio-scsi-single",
  "bootdisk": "scsi0",
  "disks": [
    {
      "slot": "scsi0",
      "size": "64G",
      "type": "disk",
      "storage": "Internal",
      "iothread": true,
      "format": "qcow2",
      "discard": true,
      "cache": "writeback"
    },
    {"slot": "ide1", "type": "cloudinit", "storage": "local"}
  ],
  "networks": [
    {"id": 0, "model": "virtio", "bridge": "vmbr1", "firewall": true}
  ],
  "cloudinit": {
    "enabled": true,
    "ipconfig": [
      {"interface": "net0", "ip": "172.16.10.100/24", "gateway": "172.16.10.1"}
    ]
  },
  "agent": 1,
  "depends_on": ["PF-01-RTR"]
}
```

### Other Available VMs

The `vms.json` also contains configurations for:

- **FLEET-01-SRV**: Ubuntu Server for Elastic Fleet (VMID 203)
- **XDR-01-SRV**: Ubuntu Server for XDR (VMID 204)
- **LIN-01-WS**: Ubuntu Desktop Workstation (VMID 205)
- **WIN-01-WS**: Windows 11 Workstation (VMID 206)


## Troubleshooting

### VMs Not Booting
- **UEFI VMs**: Ensure `bios: "ovmf"`, `machine: "q35"`, and `efi_storage` are set.
- **Legacy VMs**: Use `bios: "seabios"` (or omit the field).

### CloudInit Not Working
- Verify the CloudInit drive is defined in the `disks` array.
- Ensure `cloudinit.enabled: true` is set.
- Check that template passwords are configured in `terraform.tfvars`.

### Snapshots Not Working
- Ensure all disks use `format: "qcow2"` (not `raw`).
- EFI disks may not support snapshots in some Proxmox versions.

### Dependency Issues
- Ensure dependent VMs reference the correct VM name in `depends_on`.
- The router (`PF-01-RTR`) should not have any dependencies.

## Best Practices

1. **Always use `qcow2` format** for disks to enable snapshots.
2. **Enable `discard` and `writeback` cache** for SSD storage.
3. **Use template-based passwords** to simplify credential management.
4. **Tag VMs** for better organization in Proxmox.
5. **Set `onboot: true`** for critical infrastructure (routers, domain controllers).
6. **Use dependencies** to ensure VMs start in the correct order.
7. **Keep `terraform.tfvars` secure** and never commit it to version control.

## Additional Resources

- [Telmate Proxmox Provider Documentation](https://registry.terraform.io/providers/Telmate/proxmox/latest/docs)
- [Proxmox VE Documentation](https://pve.proxmox.com/pve-docs/)
- [CloudInit Documentation](https://cloudinit.readthedocs.io/)
