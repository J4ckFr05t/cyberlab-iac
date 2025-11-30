# Read VM configuration from JSON file
locals {
  vm_config = jsondecode(file("${path.module}/vms.json"))
  vms       = { for vm in local.vm_config.vms : vm.name => vm }
  # Split VMs into two groups: those with lifecycle rules and those without
  vms_with_lifecycle = {
    for k, v in local.vms : k => v if try(v.ignore_network_changes, false) == true
  }
  vms_without_lifecycle = {
    for k, v in local.vms : k => v if try(v.ignore_network_changes, false) != true
  }
}

# Create VMs with lifecycle rules (ignore network changes)
resource "proxmox_vm_qemu" "vms_with_lifecycle" {
  for_each    = local.vms_with_lifecycle
  name        = each.value.name
  target_node = each.value.target_node
  clone       = each.value.clone
  full_clone  = each.value.full_clone

  # CPU configuration
  cpu {
    cores   = each.value.cpu.cores
    sockets = each.value.cpu.sockets
    type    = each.value.cpu.type
  }

  memory   = each.value.memory
  scsihw   = each.value.scsihw
  bootdisk = each.value.bootdisk

  # Dynamic disk configuration
  dynamic "disk" {
    for_each = each.value.disks
    content {
      slot     = disk.value.slot
      size     = disk.value.size
      type     = disk.value.type
      storage  = disk.value.storage
      iothread = disk.value.iothread
    }
  }

  # Dynamic network configuration
  dynamic "network" {
    for_each = each.value.networks
    content {
      id       = network.value.id
      model    = network.value.model
      bridge   = network.value.bridge
      firewall = network.value.firewall
    }
  }

  # Lifecycle block to ignore network changes
  lifecycle {
    ignore_changes = [network]
  }
}

# Create VMs without lifecycle rules
resource "proxmox_vm_qemu" "vms_without_lifecycle" {
  for_each    = local.vms_without_lifecycle
  name        = each.value.name
  target_node = each.value.target_node
  clone       = each.value.clone
  full_clone  = each.value.full_clone

  # CPU configuration
  cpu {
    cores   = each.value.cpu.cores
    sockets = each.value.cpu.sockets
    type    = each.value.cpu.type
  }

  memory   = each.value.memory
  scsihw   = each.value.scsihw
  bootdisk = each.value.bootdisk

  # Dynamic disk configuration
  dynamic "disk" {
    for_each = each.value.disks
    content {
      slot     = disk.value.slot
      size     = disk.value.size
      type     = disk.value.type
      storage  = disk.value.storage
      iothread = disk.value.iothread
    }
  }

  # Dynamic network configuration
  dynamic "network" {
    for_each = each.value.networks
    content {
      id       = network.value.id
      model    = network.value.model
      bridge   = network.value.bridge
      firewall = network.value.firewall
    }
  }
}

