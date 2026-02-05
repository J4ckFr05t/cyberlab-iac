# Read VM configuration from JSON file
locals {
  vm_config = jsondecode(file("${path.module}/vms.json"))
  vms       = { for vm in local.vm_config.vms : vm.name => vm }
  
  # Map templates to their default usernames
  template_usernames = {
    "ubuntu-server-template"  = "sysadmin"
    "ubuntu-desktop-template" = "sysadmin"
    "win11-template"          = "Administrator"
    "win-dc-2022-template"    = "Administrator"
  }

  # Split VMs based on dependency tiers
  
  # Tier 0: No dependencies (e.g., Router)
  vms_tier_0 = {
    for k, v in local.vms : k => v if try(v.depends_on, null) == null || length(try(v.depends_on, [])) == 0
  }

  # Tier 1: 1 dependency (e.g., DC depends on Router)
  vms_tier_1 = {
    for k, v in local.vms : k => v if length(try(v.depends_on, [])) == 1
  }

  # Tier 2: 2+ dependencies (e.g., Workloads depend on Router + DC)
  vms_tier_2 = {
    for k, v in local.vms : k => v if length(try(v.depends_on, [])) >= 2
  }
}

# --- TIER 0 RESOURCES ---
resource "proxmox_vm_qemu" "tier_0" {
  for_each    = local.vms_tier_0
  name        = each.value.name
  target_node = each.value.target_node
  vmid        = each.value.vmid
  clone       = each.value.clone
  full_clone  = each.value.full_clone
  onboot      = try(each.value.onboot, false)

  cpu {
    cores   = each.value.cpu.cores
    sockets = each.value.cpu.sockets
    type    = each.value.cpu.type
  }

  memory   = each.value.memory
  balloon  = try(each.value.balloon, each.value.memory)
  scsihw   = each.value.scsihw
  bootdisk = each.value.bootdisk
  agent    = try(each.value.agent, 0)
  os_type  = try(each.value.os_type, null)
  bios     = try(each.value.bios, "seabios")
  machine  = try(each.value.machine, "pc")
  tags     = try(length(each.value.tags) > 0 ? join(";", each.value.tags) : null, null)
  
  # Suppress IPv6 warning as per user request
  skip_ipv6 = true

  dynamic "efidisk" {
    for_each = try(each.value.bios, "") == "ovmf" ? [1] : []
    content {
      storage           = try(each.value.efi_storage, "local-lvm")
      efitype           = "4m"
      pre_enrolled_keys = true
    }
  }

  dynamic "serial" {
    for_each = try(each.value.serial, null) != null ? [each.value.serial] : []
    content {
      id   = serial.value.id
      type = serial.value.type
    }
  }

  dynamic "disk" {
    for_each = each.value.disks
    content {
      slot     = disk.value.slot
      size     = disk.value.type == "disk" ? try(disk.value.size, null) : null
      type     = disk.value.type
      storage  = disk.value.storage
      iothread = try(disk.value.iothread, false)
      discard  = try(disk.value.discard, null)
      cache    = try(disk.value.cache, null)
    }
  }

  dynamic "network" {
    for_each = each.value.networks
    content {
      id       = network.value.id
      model    = network.value.model
      bridge   = network.value.bridge
      firewall = network.value.firewall
    }
  }

  ipconfig0 = try(each.value.cloudinit.enabled, false) && length(try(each.value.cloudinit.ipconfig, [])) > 0 ? (
    try(each.value.cloudinit.ipconfig[0].gateway, null) != null ? 
      "ip=${each.value.cloudinit.ipconfig[0].ip},gw=${each.value.cloudinit.ipconfig[0].gateway}" : 
      "ip=${each.value.cloudinit.ipconfig[0].ip}"
  ) : null

  ipconfig1 = try(each.value.cloudinit.enabled, false) && length(try(each.value.cloudinit.ipconfig, [])) > 1 ? (
    try(each.value.cloudinit.ipconfig[1].gateway, null) != null ? 
      "ip=${each.value.cloudinit.ipconfig[1].ip},gw=${each.value.cloudinit.ipconfig[1].gateway}" : 
      "ip=${each.value.cloudinit.ipconfig[1].ip}"
  ) : null

  ciuser     = try(each.value.cloudinit.enabled, false) ? lookup(local.template_usernames, each.value.clone, "sysadmin") : null
  cipassword = try(each.value.cloudinit.enabled, false) ? try(var.template_passwords[each.value.clone], null) : null
  nameserver = try(each.value.cloudinit.enabled, false) ? try(each.value.cloudinit.nameserver, null) : null
  searchdomain = try(each.value.cloudinit.enabled, false) ? try(each.value.cloudinit.searchdomain, null) : null
  sshkeys    = try(each.value.cloudinit.enabled, false) && try(each.value.cloudinit.sshkeys, null) != null ? try(join("\n", each.value.cloudinit.sshkeys), "${each.value.cloudinit.sshkeys}\n") : null

  timeouts {
    create = "40m"
  }
}

# --- TIER 1 RESOURCES (Depend on Tier 0) ---
resource "proxmox_vm_qemu" "tier_1" {
  for_each    = local.vms_tier_1
  name        = each.value.name
  target_node = each.value.target_node
  vmid        = each.value.vmid
  clone       = each.value.clone
  full_clone  = each.value.full_clone
  onboot      = try(each.value.onboot, false)

  cpu {
    cores   = each.value.cpu.cores
    sockets = each.value.cpu.sockets
    type    = each.value.cpu.type
  }

  memory   = each.value.memory
  balloon  = try(each.value.balloon, each.value.memory)
  scsihw   = each.value.scsihw
  bootdisk = each.value.bootdisk
  agent    = try(each.value.agent, 0)
  os_type  = try(each.value.os_type, null)
  bios     = try(each.value.bios, "seabios")
  machine  = try(each.value.machine, "pc")
  tags     = try(length(each.value.tags) > 0 ? join(";", each.value.tags) : null, null)

  # Suppress IPv6 warning as per user request
  skip_ipv6 = true

  dynamic "efidisk" {
    for_each = try(each.value.bios, "") == "ovmf" ? [1] : []
    content {
      storage           = try(each.value.efi_storage, "local-lvm")
      efitype           = "4m"
      pre_enrolled_keys = true
    }
  }

  dynamic "serial" {
    for_each = try(each.value.serial, null) != null ? [each.value.serial] : []
    content {
      id   = serial.value.id
      type = serial.value.type
    }
  }

  dynamic "disk" {
    for_each = each.value.disks
    content {
      slot     = disk.value.slot
      size     = disk.value.type == "disk" ? try(disk.value.size, null) : null
      type     = disk.value.type
      storage  = disk.value.storage
      iothread = try(disk.value.iothread, false)
      discard  = try(disk.value.discard, null)
      cache    = try(disk.value.cache, null)
    }
  }

  dynamic "network" {
    for_each = each.value.networks
    content {
      id       = network.value.id
      model    = network.value.model
      bridge   = network.value.bridge
      firewall = network.value.firewall
    }
  }

  ipconfig0 = try(each.value.cloudinit.enabled, false) && length(try(each.value.cloudinit.ipconfig, [])) > 0 ? (
    try(each.value.cloudinit.ipconfig[0].gateway, null) != null ? 
      "ip=${each.value.cloudinit.ipconfig[0].ip},gw=${each.value.cloudinit.ipconfig[0].gateway}" : 
      "ip=${each.value.cloudinit.ipconfig[0].ip}"
  ) : null

  ipconfig1 = try(each.value.cloudinit.enabled, false) && length(try(each.value.cloudinit.ipconfig, [])) > 1 ? (
    try(each.value.cloudinit.ipconfig[1].gateway, null) != null ? 
      "ip=${each.value.cloudinit.ipconfig[1].ip},gw=${each.value.cloudinit.ipconfig[1].gateway}" : 
      "ip=${each.value.cloudinit.ipconfig[1].ip}"
  ) : null

  ciuser     = try(each.value.cloudinit.enabled, false) ? lookup(local.template_usernames, each.value.clone, "sysadmin") : null
  cipassword = try(each.value.cloudinit.enabled, false) ? try(var.template_passwords[each.value.clone], null) : null
  nameserver = try(each.value.cloudinit.enabled, false) ? try(each.value.cloudinit.nameserver, null) : null
  searchdomain = try(each.value.cloudinit.enabled, false) ? try(each.value.cloudinit.searchdomain, null) : null
  sshkeys    = try(each.value.cloudinit.enabled, false) && try(each.value.cloudinit.sshkeys, null) != null ? try(join("\n", each.value.cloudinit.sshkeys), "${each.value.cloudinit.sshkeys}\n") : null

  timeouts {
    create = "40m"
  }

  depends_on = [proxmox_vm_qemu.tier_0]
}

# --- TIER 2 RESOURCES (Depend on Tier 1) ---
resource "proxmox_vm_qemu" "tier_2" {
  for_each    = local.vms_tier_2
  name        = each.value.name
  target_node = each.value.target_node
  vmid        = each.value.vmid
  clone       = each.value.clone
  full_clone  = each.value.full_clone
  onboot      = try(each.value.onboot, false)

  cpu {
    cores   = each.value.cpu.cores
    sockets = each.value.cpu.sockets
    type    = each.value.cpu.type
  }

  memory   = each.value.memory
  balloon  = try(each.value.balloon, each.value.memory)
  scsihw   = each.value.scsihw
  bootdisk = each.value.bootdisk
  agent    = try(each.value.agent, 0)
  os_type  = try(each.value.os_type, null)
  bios     = try(each.value.bios, "seabios")
  machine  = try(each.value.machine, "pc")
  tags     = try(length(each.value.tags) > 0 ? join(";", each.value.tags) : null, null)

  # Suppress IPv6 warning as per user request
  skip_ipv6 = true

  dynamic "efidisk" {
    for_each = try(each.value.bios, "") == "ovmf" ? [1] : []
    content {
      storage           = try(each.value.efi_storage, "local-lvm")
      efitype           = "4m"
      pre_enrolled_keys = true
    }
  }

  dynamic "serial" {
    for_each = try(each.value.serial, null) != null ? [each.value.serial] : []
    content {
      id   = serial.value.id
      type = serial.value.type
    }
  }

  dynamic "disk" {
    for_each = each.value.disks
    content {
      slot     = disk.value.slot
      size     = disk.value.type == "disk" ? try(disk.value.size, null) : null
      type     = disk.value.type
      storage  = disk.value.storage
      iothread = try(disk.value.iothread, false)
      discard  = try(disk.value.discard, null)
      cache    = try(disk.value.cache, null)
    }
  }

  dynamic "network" {
    for_each = each.value.networks
    content {
      id       = network.value.id
      model    = network.value.model
      bridge   = network.value.bridge
      firewall = network.value.firewall
    }
  }

  ipconfig0 = try(each.value.cloudinit.enabled, false) && length(try(each.value.cloudinit.ipconfig, [])) > 0 ? (
    try(each.value.cloudinit.ipconfig[0].gateway, null) != null ? 
      "ip=${each.value.cloudinit.ipconfig[0].ip},gw=${each.value.cloudinit.ipconfig[0].gateway}" : 
      "ip=${each.value.cloudinit.ipconfig[0].ip}"
  ) : null

  ipconfig1 = try(each.value.cloudinit.enabled, false) && length(try(each.value.cloudinit.ipconfig, [])) > 1 ? (
    try(each.value.cloudinit.ipconfig[1].gateway, null) != null ? 
      "ip=${each.value.cloudinit.ipconfig[1].ip},gw=${each.value.cloudinit.ipconfig[1].gateway}" : 
      "ip=${each.value.cloudinit.ipconfig[1].ip}"
  ) : null

  ciuser     = try(each.value.cloudinit.enabled, false) ? lookup(local.template_usernames, each.value.clone, "sysadmin") : null
  cipassword = try(each.value.cloudinit.enabled, false) ? try(var.template_passwords[each.value.clone], null) : null
  nameserver = try(each.value.cloudinit.enabled, false) ? try(each.value.cloudinit.nameserver, null) : null
  searchdomain = try(each.value.cloudinit.enabled, false) ? try(each.value.cloudinit.searchdomain, null) : null
  sshkeys    = try(each.value.cloudinit.enabled, false) && try(each.value.cloudinit.sshkeys, null) != null ? try(join("\n", each.value.cloudinit.sshkeys), "${each.value.cloudinit.sshkeys}\n") : null

  timeouts {
    create = "40m"
  }

  depends_on = [proxmox_vm_qemu.tier_1]
}
