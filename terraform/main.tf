resource "proxmox_vm_qemu" "pf-01-rtr-test" {
  name        = "pf-01-rtr-test"
  target_node = "proxmox"
  clone       = "pfsense-template"
  full_clone  = true
  
  # Basic VM settings
  cpu {
    cores  = 1
    sockets = 1
    type   = "host"
  }
  memory      = 2048
  scsihw      = "virtio-scsi-pci"
  bootdisk    = "scsi0"

  disk {
    slot     = "scsi0"
    size     = "32G"
    type     = "disk"
    storage  = "Internal"
    iothread = true
  }

  # WAN Interface
  network {
    id       = 0
    model    = "virtio"
    bridge   = "vmbr0"
    firewall = true
  }

  # LAN Interface
  network {
    id       = 1
    model    = "virtio"
    bridge   = "vmbr1"
    firewall = true
  }
  
  # Lifecycle to ignore changes to disk and network after creation if needed
  lifecycle {
    ignore_changes = [
      network,
    ]
  }
}

