variable "proxmox_api_url" {
  type        = string
  description = "Proxmox API URL (e.g., https://192.168.1.100:8006/api2/json)"
}

variable "proxmox_api_token_id" {
  type        = string
  description = "Proxmox API Token ID"
  sensitive   = true
}

variable "proxmox_api_token_secret" {
  type        = string
  description = "Proxmox API Token Secret"
  sensitive   = true
}

variable "template_passwords" {
  type        = map(string)
  description = "Map of template names to their cloudinit passwords"
  sensitive   = true
  default     = {}
}


