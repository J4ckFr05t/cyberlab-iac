#!/usr/bin/env python3
import os
import sys
import subprocess
import shutil
import json
import yaml

# ANSI Colors
GREEN = "\033[92m"
RED = "\033[91m"
CYAN = "\033[96m"
YELLOW = "\033[93m"
RESET = "\033[0m"

class CyberLabManager:
    def __init__(self):
        self.base_dir = os.path.dirname(os.path.abspath(__file__))
        self.terraform_dir = os.path.join(self.base_dir, 'terraform')
        self.ansible_dir = os.path.join(self.base_dir, 'ansible')
        
        # Define playbooks centrally
        self.playbooks = [
            ("check_connectivity.yml", "Check Connectivity"),
            ("dc_setup.yml", "Domain Controller Setup"),
            ("join_to_domain.yml", "Join to Domain"),
            ("siem_stack.yml", "SIEM Stack (ELK & Fleet)"),
            ("enroll_elastic_agents.yml", "Enroll Elastic Agents"),
            ("setup_wazuh.yml", "Wazuh Manager Setup"),
            ("enroll_wazuh_agents.yml", "Enroll Wazuh Agents")
        ]

    def print_status(self, message, status="INFO"):
        if status == "SUCCESS":
            print(f"[{GREEN}OK{RESET}] {message}")
        elif status == "ERROR":
            print(f"[{RED}FAIL{RESET}] {message}")
        elif status == "INFO":
            print(f"[{CYAN}INFO{RESET}] {message}")
        elif status == "WARN":
            print(f"[{YELLOW}WARN{RESET}] {message}")

    def check_tool(self, tool_name):
        path = shutil.which(tool_name)
        if path:
            self.print_status(f"Found {tool_name} at {path}", "SUCCESS")
            return True
        else:
            self.print_status(f"{tool_name} is not installed or not in PATH", "ERROR")
            return False

    def check_file(self, filepath, description):
        if os.path.exists(filepath):
            self.print_status(f"Found {description}: {os.path.basename(filepath)}", "SUCCESS")
            return True
        else:
            self.print_status(f"Missing {description}: {filepath}", "ERROR")
            return False

    def get_ssh_key(self):
        rsa_key = os.path.expanduser('~/.ssh/id_rsa.pub')
        ed25519_key = os.path.expanduser('~/.ssh/id_ed25519.pub')
        
        options = [('Manual input', None)]
        
        if os.path.exists(rsa_key):
            options.append((f"Read from {rsa_key}", rsa_key))
        if os.path.exists(ed25519_key):
            options.append((f"Read from {ed25519_key}", ed25519_key))
            
        print(f"\n{CYAN}Select SSH Public Key source:{RESET}")
        for i, (desc, _) in enumerate(options, 1):
            print(f"{i}. {desc}")
            
        while True:
            try:
                choice = int(input(f"Select option (1-{len(options)}): "))
                if 1 <= choice <= len(options):
                    desc, path = options[choice-1]
                    if path:
                        try:
                            with open(path, 'r') as f:
                                key = f.read().strip()
                                print(f"Read key: {key[:20]}...{key[-20:]}")
                                return key
                        except Exception as e:
                            self.print_status(f"Failed to read key: {e}", "ERROR")
                            return input("Enter SSH Public Key: ").strip()
                    else:
                        return input("Enter SSH Public Key: ").strip()
            except ValueError:
                pass
            print("Invalid input.")

    def check_vms_json(self):
        print(f"\n{YELLOW}Checking Terraform VM Configuration (vms.json):{RESET}")
        vms_json_path = os.path.join(self.terraform_dir, 'vms.json')
        vms_example_path = os.path.join(self.terraform_dir, 'vms.json.example')
        
        create_new = False
        if os.path.exists(vms_json_path):
            self.print_status("Found vms.json", "SUCCESS")
            # Skip reconfiguration prompt if file already exists
        else:
            self.print_status("Missing vms.json", "WARN")
            if input("Create vms.json from example? (y/n): ").lower() == 'y':
                create_new = True
            else:
                 self.print_status("vms.json is required for Terraform.", "ERROR")
                 return

        if create_new:
            if not os.path.exists(vms_example_path):
                self.print_status("Missing vms.json.example. Cannot create vms.json automatically.", "ERROR")
                return

            try:
                print(f"{CYAN}To configure cloud-init, please provide the following (applied to all VMs):{RESET}")
                search_domain = input("Enter Search Domain (e.g. yourdomain.com): ").strip()
                ssh_key = self.get_ssh_key()
                
                with open(vms_example_path, 'r') as f:
                    data = json.load(f)
                
                # Update cloudinit for all entries
                # Structure is {"vms": [...]}
                if isinstance(data, dict) and 'vms' in data and isinstance(data['vms'], list):
                    for vm in data['vms']:
                        if 'cloudinit' in vm:
                            if 'searchdomain' in vm['cloudinit']:
                                vm['cloudinit']['searchdomain'] = search_domain
                            if 'sshkeys' in vm['cloudinit']:
                                vm['cloudinit']['sshkeys'] = ssh_key
                elif isinstance(data, list):
                    # Fallback if structure changes
                     for vm in data:
                        if 'cloudinit' in vm:
                            if 'searchdomain' in vm['cloudinit']:
                                vm['cloudinit']['searchdomain'] = search_domain
                            if 'sshkeys' in vm['cloudinit']:
                                vm['cloudinit']['sshkeys'] = ssh_key
                
                with open(vms_json_path, 'w') as f:
                    json.dump(data, f, indent=2)
                
                self.print_status(f"Created and configured {vms_json_path}", "SUCCESS")
                
            except Exception as e:
                self.print_status(f"Failed to create vms.json: {e}", "ERROR")

    def run_command_stream(self, command, cwd, description):
        self.print_status(f"Running: {description}...", "INFO")
        print(f"{CYAN}{'-'*40}{RESET}")
        try:
            process = subprocess.Popen(
                command,
                cwd=cwd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                shell=True
            )
            for line in process.stdout:
                print(line, end='')
            
            process.wait()
            print(f"{CYAN}{'-'*40}{RESET}")
            
            if process.returncode == 0:
                self.print_status(f"{description} completed successfully.", "SUCCESS")
                return True
            else:
                self.print_status(f"{description} failed with exit code {process.returncode}.", "ERROR")
                return False
        except Exception as e:
            self.print_status(f"Failed to execute {description}: {e}", "ERROR")
            return False

    def create_terraform_secrets(self, tf_vars_path):
        """Create terraform.tfvars file with Proxmox credentials and template passwords."""
        try:
            print(f"\n{CYAN}Configuring Terraform secrets:{RESET}")
            
            # Get Proxmox API details
            proxmox_api_url = input("Enter Proxmox API URL (e.g., https://your-proxmox-server:8006/api2/json): ").strip()
            proxmox_api_token_id = input("Enter Proxmox API Token ID (e.g., your-token-id@pam!your-token-name): ").strip()
            proxmox_api_token_secret = input("Enter Proxmox API Token Secret: ").strip()
            
            # Get template passwords
            print(f"\n{YELLOW}Configure passwords for VM templates:{RESET}")
            templates = [
                "ubuntu-server-template",
                "ubuntu-desktop-template",
                "win11-template",
                "win-dc-2022-template"
            ]
            
            use_same_password = input("Use the same password for all templates? (y/n): ").lower().strip() == 'y'
            template_passwords = {}
            
            if use_same_password:
                common_password = input("Enter password for all templates: ").strip()
                if common_password:
                    for template in templates:
                        template_passwords[template] = common_password
            else:
                print("Enter passwords for each template (press Enter to skip):")
                for template in templates:
                    password = input(f"Password for {template}: ").strip()
                    if password:
                        template_passwords[template] = password
            
            # Build the terraform.tfvars content
            content = "# Proxmox API Configuration\n"
            content += f'proxmox_api_url          = "{proxmox_api_url}"\n'
            content += f'proxmox_api_token_id     = "{proxmox_api_token_id}"\n'
            content += f'proxmox_api_token_secret = "{proxmox_api_token_secret}"\n'
            content += "\n# Template-based passwords\n"
            content += "# All VMs using the same template will share the same password\n"
            content += "template_passwords = {\n"
            
            for template, password in template_passwords.items():
                content += f'  "{template}" = "{password}"\n'
            
            content += "}\n"
            
            # Write the file
            with open(tf_vars_path, 'w') as f:
                f.write(content)
            
            # Set restrictive permissions (owner read/write only)
            os.chmod(tf_vars_path, 0o600)
            
            self.print_status(f"Created {os.path.basename(tf_vars_path)}", "SUCCESS")
            return True
            
        except Exception as e:
            self.print_status(f"Failed to create Terraform secrets: {e}", "ERROR")
            return False

    def create_vault_pass(self, vault_pass_path):
        """Create Ansible vault password file."""
        try:
            print(f"\n{CYAN}Creating Ansible Vault password file:{RESET}")
            password = input("Enter Ansible Vault password: ").strip()
            
            if not password:
                self.print_status("Password cannot be empty.", "ERROR")
                return False
            
            # Write the password file
            with open(vault_pass_path, 'w') as f:
                f.write(password + '\n')
            
            # Set restrictive permissions (owner read/write only)
            os.chmod(vault_pass_path, 0o600)
            
            self.print_status(f"Created {os.path.basename(vault_pass_path)}", "SUCCESS")
            return True
            
        except Exception as e:
            self.print_status(f"Failed to create Vault password file: {e}", "ERROR")
            return False

    def domain_to_ldap_dn(self, domain_name):
        """Convert domain name to LDAP DN format.
        
        Example:
            'example.com' -> 'DC=example,DC=com'
            'domain1.parent.com' -> 'DC=domain1,DC=parent,DC=com'
        """
        parts = domain_name.split('.')
        return ','.join([f'DC={part}' for part in parts])

    def create_all_yml(self, all_yml_path):
        """Create ansible/inventory/group_vars/all.yml with domain configuration."""
        try:
            print(f"\n{CYAN}Configuring Domain Settings for all.yml:{RESET}")
            
            domain_name = input("Enter Domain Name (e.g., example.com or domain1.parent.com): ").strip()
            if not domain_name:
                self.print_status("Domain name cannot be empty.", "ERROR")
                return False, None, None, None
            
            domain_netbios_name = input("Enter Domain NetBIOS Name (e.g., EXAMPLE): ").strip()
            if not domain_netbios_name:
                self.print_status("Domain NetBIOS name cannot be empty.", "ERROR")
                return False, None, None, None
            
            print("Enter DNS Forwarders (press Enter after each, empty line to finish):")
            dns_forwarders = []
            while True:
                forwarder = input("  DNS Forwarder (or Enter to finish): ").strip()
                if not forwarder:
                    break
                dns_forwarders.append(forwarder)
            
            if not dns_forwarders:
                # Default to Google DNS if none provided
                dns_forwarders = ['8.8.8.8', '8.8.4.4']
                self.print_status("No DNS forwarders provided, using defaults: 8.8.8.8, 8.8.4.4", "WARN")
            
            # Build YAML content
            yaml_content = """---
# Variables for all hosts
# Domain Configuration
domain_name: {domain_name}
domain_netbios_name: {domain_netbios_name}

# DNS Configuration
dns_forwarders:
""".format(
                domain_name=domain_name,
                domain_netbios_name=domain_netbios_name
            )
            
            for forwarder in dns_forwarders:
                yaml_content += f"  - {forwarder}\n"
            
            # Write the file
            with open(all_yml_path, 'w') as f:
                f.write(yaml_content)
            
            self.print_status(f"Created {os.path.basename(all_yml_path)}", "SUCCESS")
            return True, domain_name, domain_netbios_name, dns_forwarders
            
        except Exception as e:
            self.print_status(f"Failed to create all.yml: {e}", "ERROR")
            return False, None, None, None

    def create_dc_yml(self, dc_yml_path, domain_name, domain_netbios_name, dns_forwarders):
        """Create ansible/inventory/group_vars/dc.yml with domain controller configuration."""
        try:
            # Convert domain name to LDAP DN format
            ldap_dn = self.domain_to_ldap_dn(domain_name)
            
            # Build YAML content
            yaml_content = """---
# Domain Controller Variables
# These variables are used by the dc_setup role

# Domain Configuration
domain_name: {domain_name}
domain_netbios_name: {domain_netbios_name}

# DNS Configuration
dns_forwarders:
""".format(
                domain_name=domain_name,
                domain_netbios_name=domain_netbios_name
            )
            
            for forwarder in dns_forwarders:
                yaml_content += f"  - {forwarder}\n"
            
            # Add organizational units with dynamic LDAP DN
            yaml_content += f"""
# Organizational Units to create
organizational_units:
  - name: Workstations
    path: "{ldap_dn}"
  - name: Windows Workstations
    path: "OU=Workstations,{ldap_dn}"
  - name: Linux Workstations
    path: "OU=Workstations,{ldap_dn}"
  - name: Servers
    path: "{ldap_dn}"
  - name: Windows Servers
    path: "OU=Servers,{ldap_dn}"
  - name: Linux Servers
    path: "OU=Servers,{ldap_dn}"

# Domain Users to create
domain_users:
  - display_name: Dave Johnson
    firstname: Dave
    lastname: Johnson
    password: "{{{{ dave_password }}}}"
    enabled: yes
    password_never_expires: no
    user_cannot_change_password: no
  - display_name: Sophia Davis
    firstname: Sophia
    lastname: Davis
    password: "{{{{ sophia_password }}}}"
    enabled: yes
    password_never_expires: no
    user_cannot_change_password: no

# WinRM Configuration
ansible_connection: winrm
ansible_winrm_transport: ntlm
ansible_winrm_server_cert_validation: ignore
ansible_port: 5985

# Disable become (sudo) - not applicable for Windows
ansible_become: false
ansible_become_method: runas

"""
            
            # Write the file
            with open(dc_yml_path, 'w') as f:
                f.write(yaml_content)
            
            self.print_status(f"Created {os.path.basename(dc_yml_path)}", "SUCCESS")
            return True
            
        except Exception as e:
            self.print_status(f"Failed to create dc.yml: {e}", "ERROR")
            return False

    def create_ansible_vault(self, vault_path, vault_pass_path):
        """Create Ansible vault file with encrypted secrets."""
        try:
            print(f"\n{CYAN}Configuring Ansible Vault secrets:{RESET}")
            
            # Read vault password
            with open(vault_pass_path, 'r') as f:
                vault_password = f.read().strip()
            
            # Collect all required secrets
            print(f"\n{YELLOW}Enter the following credentials:{RESET}")
            win_username = input("Windows/AD Administrator Username (default: Administrator): ").strip() or "Administrator"
            win_password = input("Windows/AD Administrator Password: ").strip()
            dsrm_password = input("Domain Recovery (DSRM) Password: ").strip()
            dave_password = input("Dave User Password: ").strip()
            sophia_password = input("Sophia User Password: ").strip()
            elastic_custom_password = input("Elastic Custom Password: ").strip()
            wazuh_api_password = input("Wazuh API Password: ").strip()
            wazuh_admin_password = input("Wazuh Admin Password: ").strip()
            
            # Build the YAML content
            vault_content = """---
# Windows/AD Administrator
win_username: {win_username}
win_password: {win_password}

# Domain Recovery
dsrm_password: {dsrm_password}

# User Passwords
dave_password: {dave_password}
sophia_password: {sophia_password}

# ELK Stack
elastic_custom_password: {elastic_custom_password}

# Wazuh
wazuh_api_password: {wazuh_api_password}
wazuh_admin_password: {wazuh_admin_password}
""".format(
                win_username=win_username,
                win_password=win_password,
                dsrm_password=dsrm_password,
                dave_password=dave_password,
                sophia_password=sophia_password,
                elastic_custom_password=elastic_custom_password,
                wazuh_api_password=wazuh_api_password,
                wazuh_admin_password=wazuh_admin_password
            )
            
            # Create a temporary file with the content
            import tempfile
            with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.yml') as tmp_file:
                tmp_file.write(vault_content)
                tmp_file_path = tmp_file.name
            
            try:
                # Use ansible-vault to encrypt the file
                # ansible-vault encrypt --encrypt-vault-id default --vault-password-file <pass_file> <vault_file>
                cmd = f'ansible-vault encrypt --encrypt-vault-id default --vault-password-file "{vault_pass_path}" "{tmp_file_path}"'
                result = subprocess.run(
                    cmd,
                    shell=True,
                    capture_output=True,
                    text=True,
                    cwd=self.ansible_dir
                )
                
                if result.returncode != 0:
                    self.print_status(f"Failed to encrypt vault: {result.stderr}", "ERROR")
                    os.unlink(tmp_file_path)
                    return False
                
                # Move the encrypted file to the target location
                shutil.move(tmp_file_path, vault_path)
                
                # Set restrictive permissions
                os.chmod(vault_path, 0o600)
                
                self.print_status(f"Created encrypted {os.path.basename(vault_path)}", "SUCCESS")
                return True
                
            except Exception as e:
                # Clean up temp file on error
                if os.path.exists(tmp_file_path):
                    os.unlink(tmp_file_path)
                raise e
            
        except Exception as e:
            self.print_status(f"Failed to create Ansible Vault: {e}", "ERROR")
            return False

    def check_prerequisites(self):
        print(f"\n{CYAN}=== Checking Prerequisites ==={RESET}")
        all_checks_passed = True

        # 1. Check System Tools
        print(f"\n{YELLOW}Checking System Tools:{RESET}")
        tools = ['terraform', 'ansible', 'ansible-playbook']
        for tool in tools:
            if not self.check_tool(tool):
                all_checks_passed = False

        # 1.1 Check vms.json
        self.check_vms_json()
        if not os.path.exists(os.path.join(self.terraform_dir, 'vms.json')):
            all_checks_passed = False

        # 1.2 Check Ansible Group Vars
        print(f"\n{YELLOW}Checking Ansible Group Variables:{RESET}")
        all_yml_path = os.path.join(self.ansible_dir, 'inventory', 'group_vars', 'all.yml')
        dc_yml_path = os.path.join(self.ansible_dir, 'inventory', 'group_vars', 'dc.yml')
        
        domain_name = None
        domain_netbios_name = None
        dns_forwarders = None
        
        # Check all.yml
        all_yml_created = False
        if not os.path.exists(all_yml_path):
            self.print_status(f"Missing {os.path.basename(all_yml_path)}", "WARN")
            if input(f"Create {os.path.basename(all_yml_path)} now? (y/n): ").lower() == 'y':
                result = self.create_all_yml(all_yml_path)
                if isinstance(result, tuple):
                    success, domain_name, domain_netbios_name, dns_forwarders = result
                    if success:
                        all_yml_created = True
                    else:
                        all_checks_passed = False
                else:
                    all_checks_passed = False
            else:
                self.print_status(f"{os.path.basename(all_yml_path)} is required.", "ERROR")
                all_checks_passed = False
        else:
            self.print_status(f"Found {os.path.basename(all_yml_path)}", "SUCCESS")
            # Read existing values for dc.yml if needed
            try:
                with open(all_yml_path, 'r') as f:
                    all_data = yaml.safe_load(f)
                    domain_name = all_data.get('domain_name')
                    domain_netbios_name = all_data.get('domain_netbios_name')
                    dns_forwarders = all_data.get('dns_forwarders', [])
            except Exception as e:
                self.print_status(f"Could not read existing all.yml: {e}", "WARN")
        
        # Check dc.yml
        if not os.path.exists(dc_yml_path):
            self.print_status(f"Missing {os.path.basename(dc_yml_path)}", "WARN")
            if domain_name and domain_netbios_name and dns_forwarders:
                # If all.yml was just created, automatically create dc.yml without asking
                if all_yml_created:
                    self.print_status(f"Creating {os.path.basename(dc_yml_path)} automatically...", "INFO")
                    if not self.create_dc_yml(dc_yml_path, domain_name, domain_netbios_name, dns_forwarders):
                        all_checks_passed = False
                else:
                    if input(f"Create {os.path.basename(dc_yml_path)} now? (y/n): ").lower() == 'y':
                        if not self.create_dc_yml(dc_yml_path, domain_name, domain_netbios_name, dns_forwarders):
                            all_checks_passed = False
                    else:
                        self.print_status(f"{os.path.basename(dc_yml_path)} is required.", "ERROR")
                        all_checks_passed = False
            else:
                self.print_status(f"Cannot create {os.path.basename(dc_yml_path)} without domain configuration.", "ERROR")
                all_checks_passed = False
        else:
            self.print_status(f"Found {os.path.basename(dc_yml_path)}", "SUCCESS")

        # 2. Check Terraform Secrets
        print(f"\n{YELLOW}Checking Terraform Configuration:{RESET}")
        tf_vars_path = os.path.join(self.terraform_dir, 'terraform.tfvars')
        if not os.path.exists(tf_vars_path):
            self.print_status(f"Missing {tf_vars_path}", "WARN")
            if input(f"Create Terraform secrets now? (y/n): ").lower() == 'y':
                if not self.create_terraform_secrets(tf_vars_path):
                     self.print_status("Failed to create Terraform secrets.", "ERROR")
                     all_checks_passed = False
            else:
                self.print_status("Terraform secrets are required.", "ERROR")
                all_checks_passed = False
        else:
             self.print_status(f"Found Terraform Secrets: {os.path.basename(tf_vars_path)}", "SUCCESS")

        # 3. Check Ansible Secrets
        print(f"\n{YELLOW}Checking Ansible Configuration:{RESET}")
        
        # Check .vault_pass first
        vault_pass_path = os.path.join(self.ansible_dir, '.vault_pass')
        if not os.path.exists(vault_pass_path):
            self.print_status(f"Missing Vault Password File: {vault_pass_path}", "WARN")
            if input(f"Create Vault Password file now? (y/n): ").lower() == 'y':
                if not self.create_vault_pass(vault_pass_path):
                     self.print_status("Failed to create Vault Password file.", "ERROR")
                     all_checks_passed = False
            else:
                self.print_status("Vault Password file is required.", "ERROR")
                all_checks_passed = False
        else:
             self.print_status(f"Found Vault Password File: {os.path.basename(vault_pass_path)}", "SUCCESS")

        # Check secret_vault.yml
        vault_path = os.path.join(self.ansible_dir, 'inventory', 'group_vars', 'secret_vault.yml')
        if not os.path.exists(vault_path):
            self.print_status(f"Missing Ansible Vault: {vault_path}", "WARN")
            # Only allow creation if vault pass exists (either found or just created)
            if os.path.exists(vault_pass_path):
                if input(f"Create Ansible Vault now? (y/n): ").lower() == 'y':
                   if not self.create_ansible_vault(vault_path, vault_pass_path):
                       self.print_status("Failed to create Ansible Vault.", "ERROR")
                       all_checks_passed = False
                else:
                    self.print_status("Ansible Vault is required.", "ERROR")
                    all_checks_passed = False
            else:
                 self.print_status("Cannot create Vault without Password File.", "ERROR")
                 all_checks_passed = False
        else:
            self.print_status(f"Found Ansible Vault: {os.path.basename(vault_path)}", "SUCCESS")

        # 4. Terraform Init
        print(f"\n{YELLOW}Initializing Terraform:{RESET}")
        tf_dir_path = os.path.join(self.terraform_dir, '.terraform')
        if not os.path.exists(tf_dir_path):
            if input("Terraform not initialized. Run 'terraform init' now? (y/n): ").lower() == 'y':
                 if not self.run_command_stream("terraform init", self.terraform_dir, "Terraform Init"):
                     all_checks_passed = False
            else:
                 self.print_status("Skipping Terraform Init.", "WARN")
                 all_checks_passed = False
        else:
             self.print_status("Terraform is already initialized (.terraform directory exists).", "SUCCESS")

        # 5. Ansible Galaxy Requirements
        print(f"\n{YELLOW}Installing Ansible Requirements:{RESET}")
        requirements_path = os.path.join(self.ansible_dir, 'requirements.yml')
        if os.path.exists(requirements_path):
             if not self.run_command_stream("ansible-galaxy install -r requirements.yml", self.ansible_dir, "Ansible Galaxy Install"):
                 all_checks_passed = False
        
        if all_checks_passed:
            print(f"\n{GREEN}All prerequisites checks passed!{RESET}")
        else:
            print(f"\n{RED}Some prerequisites checks failed. Please review above.{RESET}")
        
        input(f"\nPress Enter to return to menu...")

    def deploy_vms(self):
        print(f"\n{CYAN}=== Deploy Infrastructure (Terraform) ==={RESET}")
        
        # Check vms.json
        if not os.path.exists(os.path.join(self.terraform_dir, 'vms.json')):
             self.print_status("vms.json is missing. Please run Prerequisites checks first.", "ERROR")
             input("Press Enter to return to menu...")
             return

        # 1. Terraform Plan
        print(f"\n{YELLOW}Running Terraform Plan...{RESET}")
        plan_file = "lab.tfplan"
        if not self.run_command_stream(f"terraform plan -out={plan_file}", self.terraform_dir, "Terraform Plan"):
            self.print_status("Terraform Plan failed.", "ERROR")
            input("Press Enter to return to menu...")
            return

        # 2. Confirmation
        print(f"\n{YELLOW}Please review the plan above.{RESET}")
        choice = input(f"Do you want to apply this plan? (y/n): ").lower()
        
        if choice == 'y':
            # 3. Terraform Apply
            print(f"\n{YELLOW}Applying Terraform Plan...{RESET}")
            if self.run_command_stream(f"terraform apply \"{plan_file}\"", self.terraform_dir, "Terraform Apply"):
                self.print_status("Infrastructure deployed successfully!", "SUCCESS")
                # Clean up plan file
                plan_path = os.path.join(self.terraform_dir, plan_file)
                if os.path.exists(plan_path):
                    os.remove(plan_path)
            else:
                self.print_status("Terraform Apply failed.", "ERROR")
        else:
            self.print_status("Deployment cancelled by user.", "WARN")
        
        input("\nPress Enter to return to menu...")

    def run_ansible_playbook(self, playbook_name, description, inventory_file="inventory/hosts.ini"):
        """Helper to run a single playbook."""
        print(f"\n{YELLOW}>> Starting: {description}{RESET}")
        playbook_path = f"playbooks/{playbook_name}"
        
        # Construct command
        cmd = f"ansible-playbook -i {inventory_file} {playbook_path}"
        
        if self.run_command_stream(cmd, self.ansible_dir, description):
            self.print_status(f"Finished: {description}", "SUCCESS")
            return True
        else:
            self.print_status(f"Failed: {description}", "ERROR")
            return False

    def configure_vms(self):
        print(f"\n{CYAN}=== Configure Software (Ansible) ==={RESET}")
        
        # Run clean_known_hosts.sh once upon entry
        clean_hosts_script = "scripts/clean_known_hosts.sh"
        if os.path.exists(os.path.join(self.base_dir, clean_hosts_script)):
            self.print_status("Cleaning known_hosts...", "INFO")
            os.chmod(os.path.join(self.base_dir, clean_hosts_script), 0o755)
            if not self.run_command_stream(f"./{clean_hosts_script}", self.base_dir, "Clean Known Hosts"):
                self.print_status("Failed to clean known_hosts. Continuing...", "WARN")
        else:
            self.print_status(f"Script {clean_hosts_script} not found. Skipping.", "WARN")

        while True:
            print(f"\n{CYAN}--- Ansible Configuration Menu ---{RESET}")
            print("1. Run All Playbooks (Sequential)")
            print("2. Run Specific Playbook")
            print("3. Step-by-Step Execution (Interactive)")
            print("4. Return to Main Menu")
            
            choice = input(f"\n{YELLOW}Select an option (1-4): {RESET}")
            
            if choice == '1':
                # Run All
                print(f"\n{YELLOW}Running ALL playbooks sequentially...{RESET}")
                
                # Ask for exclusions
                excluded_indices = set()
                if input(f"Do you want to exclude any playbooks? (y/n): ").lower().strip() == 'y':
                    print(f"\n{CYAN}--- Available Playbooks ---{RESET}")
                    for i, (_, desc) in enumerate(self.playbooks, 1):
                        print(f"{i}. {desc}")
                    
                    try:
                        exclusion_input = input(f"\n{YELLOW}Enter numbers to exclude (comma-separated, e.g. 1,3): {RESET}")
                        parts = [p.strip() for p in exclusion_input.split(',') if p.strip()]
                        for p in parts:
                            idx = int(p)
                            if 1 <= idx <= len(self.playbooks):
                                excluded_indices.add(idx - 1)
                    except ValueError:
                        print(f"{RED}Invalid input. Proceeding without exclusions.{RESET}")

                for i, (playbook_name, description) in enumerate(self.playbooks):
                    if i in excluded_indices:
                        print(f"{CYAN}Skipping: {description} (Excluded by user){RESET}")
                        continue
                        
                    if not self.run_ansible_playbook(playbook_name, description):
                        print(f"{RED}Stopping execution sequence due to failure.{RESET}")
                        break
                input("Press Enter to continue...")

            elif choice == '2':
                # Run Specific
                print(f"\n{CYAN}--- Available Playbooks ---{RESET}")
                for i, (_, desc) in enumerate(self.playbooks, 1):
                    print(f"{i}. {desc}")
                print(f"{len(self.playbooks) + 1}. Cancel")
                
                try:
                    pb_choice = int(input(f"\n{YELLOW}Select playbook to run (1-{len(self.playbooks) + 1}): {RESET}"))
                    if 1 <= pb_choice <= len(self.playbooks):
                        pb_name, pb_desc = self.playbooks[pb_choice - 1]
                        self.run_ansible_playbook(pb_name, pb_desc)
                        input("Press Enter to continue...")
                    elif pb_choice == len(self.playbooks) + 1:
                        continue
                    else:
                        print("Invalid selection.")
                except ValueError:
                    print("Invalid input.")

            elif choice == '3':
                # Step-by-Step
                print(f"\n{YELLOW}Starting Step-by-Step Execution...{RESET}")
                for playbook_name, description in self.playbooks:
                    action = input(f"\nRun '{description}'? (y/n/q): ").lower().strip()
                    if action == 'q':
                        print("Quitting step-by-step execution.")
                        break
                    elif action == 'y':
                        if not self.run_ansible_playbook(playbook_name, description):
                             if input(f"{RED}Playbook failed. Continue anyway? (y/n): {RESET}").lower() != 'y':
                                 break
                    else:
                        print(f"Skipping {description}...")
                input("Press Enter to continue...")

            elif choice == '4':
                return
            else:
                print("Invalid option.")

    def menu(self):
        while True:
            # os.system('clear' if os.name == 'posix' else 'cls') # Commented out clear for better scrolling history during dev
            print(f"\n{CYAN}=== CyberLab Infrastructure Manager ==={RESET}")
            print("1. Run Prerequisites Checks")
            print("2. Deploy Infrastructure (Terraform)")
            print("3. Configure Software (Ansible)")
            print("4. Exit")
            
            try:
                choice = input(f"\n{YELLOW}Select an option (1-4): {RESET}")
            except EOFError:
                break
            
            if choice == '1':
                self.check_prerequisites()
            elif choice == '2':
                self.deploy_vms()
            elif choice == '3':
                self.configure_vms()
            elif choice == '4':
                print("Exiting...")
                sys.exit(0)
            else:
                print("Invalid option. Please try again.")

if __name__ == "__main__":
    try:
        manager = CyberLabManager()
        manager.menu()
    except KeyboardInterrupt:
        print("\nExiting...")
        sys.exit(0)
