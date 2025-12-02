# Read VM configuration from JSON file
locals {
  vm_config = jsondecode(file("${path.module}/vms.json"))
  vms       = { for vm in local.vm_config.vms : vm.name => vm }
}

# Create VMs
resource "proxmox_vm_qemu" "vms" {
  for_each    = local.vms
  name        = each.value.name
  target_node = each.value.target_node
  vmid        = each.value.vmid
  clone       = each.value.clone
  full_clone  = each.value.full_clone
  onboot      = try(each.value.onboot, false)

  # CPU configuration
  cpu {
    cores   = each.value.cpu.cores
    sockets = each.value.cpu.sockets
    type    = each.value.cpu.type
  }

  memory   = each.value.memory
  scsihw   = each.value.scsihw
  bootdisk = each.value.bootdisk
  agent    = try(each.value.agent, 0)
  os_type  = try(each.value.os_type, null)
  bios     = try(each.value.bios, "seabios")
  machine  = try(each.value.machine, "pc")

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

  # Dynamic disk configuration
  dynamic "disk" {
    for_each = each.value.disks
    content {
      slot     = disk.value.slot
      size     = try(disk.value.size, null)
      type     = disk.value.type
      storage  = disk.value.storage
      iothread = try(disk.value.iothread, false)
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

  # CloudInit configuration - ipconfig as string attributes (ipconfig0, ipconfig1, etc.)
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

  # CloudInit user credentials and DNS
  # Password is read from sensitive variable instead of JSON
  # Setting cloudinit parameters automatically creates the cloudinit drive
  ciuser     = try(each.value.cloudinit.enabled, false) ? each.value.cloudinit.username : null
  cipassword = try(each.value.cloudinit.enabled, false) ? try(var.vm_passwords[each.value.name], null) : null
  nameserver = try(each.value.cloudinit.enabled, false) ? try(each.value.cloudinit.nameserver, null) : null
  sshkeys    = try(each.value.cloudinit.enabled, false) && try(each.value.cloudinit.sshkeys, null) != null ? urlencode(each.value.cloudinit.sshkeys) : null
}

