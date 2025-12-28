#!/usr/bin/env python3
import os
import sys
import subprocess
import shutil

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

    def create_terraform_secrets(self, filepath):
        print(f"\n{YELLOW}Creating {filepath}...{RESET}")
        try:
            proxmox_url = input(f"Enter Proxmox API URL (e.g. https://192.168.1.100:8006/api2/json): ").strip()
            proxmox_token_id = input(f"Enter Proxmox Token ID (e.g. root@pam!terraform): ").strip()
            proxmox_token_secret = input(f"Enter Proxmox Token Secret: ").strip()
            
            # Simple template for password entry to avoid asking 4 times if they are same
            print(f"\n{CYAN}Template Passwords (used for cloud-init user):{RESET}")
            default_password = input("Enter a default password for all VM templates: ").strip()
            
            content = f"""# Proxmox API Configuration
proxmox_api_url          = "{proxmox_url}"
proxmox_api_token_id     = "{proxmox_token_id}"
proxmox_api_token_secret = "{proxmox_token_secret}"

# Template-based passwords
template_passwords = {{
  "ubuntu-server-template"  = "{default_password}"
  "ubuntu-desktop-template" = "{default_password}"
  "win11-template"          = "{default_password}"
  "win-dc-2022-template"    = "{default_password}"
}}
"""
            with open(filepath, 'w') as f:
                f.write(content)
            self.print_status(f"Created {filepath}", "SUCCESS")
            return True
        except Exception as e:
            self.print_status(f"Failed to create {filepath}: {e}", "ERROR")
            return False

    def create_vault_pass(self, filepath):
        print(f"\n{YELLOW}Creating {filepath}...{RESET}")
        try:
            password = input("Enter Ansible Vault Password: ").strip()
            with open(filepath, 'w') as f:
                f.write(password)
            os.chmod(filepath, 0o600)
            self.print_status(f"Created {filepath}", "SUCCESS")
            return True
        except Exception as e:
            self.print_status(f"Failed to create {filepath}: {e}", "ERROR")
            return False

    def create_ansible_vault(self, filepath, vault_pass_file):
        print(f"\n{YELLOW}Creating {filepath}...{RESET}")
        temp_file = None
        try:
            print("Please provide the following credentials for the Ansible Vault:")
            win_user = input("Windows Admin Username [Administrator]: ").strip() or "Administrator"
            win_pass = input("Windows Admin Password: ").strip()
            dsrm_pass = input("Active Directory DSRM Password: ").strip()
            
            # User passwords
            dave_pass = input("Password for user 'dave' (UserPassword1!): ").strip() or "UserPassword1!"
            sophia_pass = input("Password for user 'sophia' (UserPassword2!): ").strip() or "UserPassword2!"
            
            elastic_pass = input("Elasticsearch Custom Password: ").strip()
            wazuh_api_pass = input("Wazuh API Password: ").strip()
            wazuh_admin_pass = input("Wazuh Admin Password: ").strip()

            temp_yaml = """---
# Windows/AD Administrator
win_username: {win_user}
win_password: {win_pass}

# Domain Recovery
dsrm_password: {dsrm_pass}

# User Passwords
dave_password: {dave_pass}
sophia_password: {sophia_pass}

# ELK Stack
elastic_custom_password: {elastic_pass}

# Wazuh
wazuh_api_password: {wazuh_api_pass}
wazuh_admin_password: {wazuh_admin_pass}
""".format(
    win_user=win_user, win_pass=win_pass, dsrm_pass=dsrm_pass,
    dave_pass=dave_pass, sophia_pass=sophia_pass,
    elastic_pass=elastic_pass,
    wazuh_api_pass=wazuh_api_pass, wazuh_admin_pass=wazuh_admin_pass
)
            
            temp_file = os.path.join(os.path.dirname(filepath), 'temp_vault.yml')
            with open(temp_file, 'w') as f:
                f.write(temp_yaml)
            
            cmd = f"ansible-vault encrypt {temp_file} --output {filepath}"
            if self.run_command_stream(cmd, self.ansible_dir, "Encrypting Vault"):
                os.remove(temp_file)
                self.print_status(f"Created and encrypted {filepath}", "SUCCESS")
                return True
            else:
                return False

        except Exception as e:
            self.print_status(f"Failed to create {filepath}: {e}", "ERROR")
            if temp_file and os.path.exists(temp_file):
                os.remove(temp_file)
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

    def configure_vms(self):
        print(f"\n{CYAN}=== Configure Software (Ansible) ==={RESET}")
        
        playbooks = [
            ("playbooks/dc_setup.yml", "Domain Controller Setup"),
            ("playbooks/configure_dns.yml", "DNS Configuration"),
            ("playbooks/join_to_domain.yml", "Join to Domain"),
            ("playbooks/siem_stack.yml", "SIEM Stack (ELK & Fleet)"),
            ("playbooks/enroll_elastic_agents.yml", "Enroll Elastic Agents"),
            ("playbooks/setup_wazuh.yml", "Wazuh Manager Setup"),
            ("playbooks/enroll_wazuh_agents.yml", "Enroll Wazuh Agents")
        ]

        print(f"\n{YELLOW}The following playbooks will be executed in order:{RESET}")
        for i, (_, desc) in enumerate(playbooks, 1):
            print(f"{i}. {desc}")
        
        choice = input(f"\nProceed with configuration? (y/n): ").lower()
        if choice != 'y':
            self.print_status("Configuration cancelled.", "WARN")
            return

        inventory_file = os.path.join(self.ansible_dir, 'inventory/hosts.ini')
        
        for playbook_rel_path, description in playbooks:
            print(f"\n{YELLOW}>> Starting: {description}{RESET}")
            playbook_path = os.path.join(self.ansible_dir, playbook_rel_path)
            
            # Construct command
            # Note: We assume secrets are handled by ansible.cfg pointing to .vault_pass
            cmd = f"ansible-playbook -i {inventory_file} {playbook_path}"
            
            if not self.run_command_stream(cmd, self.ansible_dir, description):
                self.print_status(f"Configuration failed at step: {description}", "ERROR")
                print(f"{RED}Stopping execution sequence.{RESET}")
                input("Press Enter to return to menu...")
                return
            
            self.print_status(f"Finished: {description}", "SUCCESS")

        print(f"\n{GREEN}All configuration steps completed successfully!{RESET}")
        input("Press Enter to return to menu...")

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
