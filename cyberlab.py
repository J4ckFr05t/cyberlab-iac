#!/usr/bin/env python3
import os
import sys
import subprocess
import shutil
import json

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
            if input("Do you want to re-configure vms.json (overwrite)? (y/n): ").lower() == 'y':
                create_new = True
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

# ... [rest of methods] ...

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

    def configure_vms(self):
        print(f"\n{CYAN}=== Configure Software (Ansible) ==={RESET}")
        
    def configure_vms(self):
        print(f"\n{CYAN}=== Configure Software (Ansible) ==={RESET}")
        
        playbooks = [
            ("check_connectivity.yml", "Check Connectivity"),
            ("dc_setup.yml", "Domain Controller Setup"),
            ("join_to_domain.yml", "Join to Domain"),
            ("siem_stack.yml", "SIEM Stack (ELK & Fleet)"),
            ("enroll_elastic_agents.yml", "Enroll Elastic Agents"),
            ("setup_wazuh.yml", "Wazuh Manager Setup"),
            ("enroll_wazuh_agents.yml", "Enroll Wazuh Agents")
        ]

        print(f"\n{YELLOW}The following playbooks will be executed in order:{RESET}")
        for i, (_, desc) in enumerate(playbooks, 1):
            print(f"{i}. {desc}")
        
        choice = input(f"\nProceed with configuration? (y/n): ").lower()
        if choice != 'y':
            self.print_status("Configuration cancelled.", "WARN")
            return

        # Run clean_known_hosts.sh
        clean_hosts_script = "scripts/clean_known_hosts.sh"
        if os.path.exists(os.path.join(self.base_dir, clean_hosts_script)):
            self.print_status("Cleaning known_hosts...", "INFO")
            # Ensure execute permission
            os.chmod(os.path.join(self.base_dir, clean_hosts_script), 0o755)
            if not self.run_command_stream(f"./{clean_hosts_script}", self.base_dir, "Clean Known Hosts"):
                self.print_status("Failed to clean known_hosts. Continuing...", "WARN")
        else:
            self.print_status(f"Script {clean_hosts_script} not found. Skipping.", "WARN")

        # Paths relative to ansible_dir (we will execute from there)
        inventory_file = "inventory/hosts.ini"
        
        for playbook_name, description in playbooks:
            print(f"\n{YELLOW}>> Starting: {description}{RESET}")
            playbook_path = f"playbooks/{playbook_name}"
            
            # Construct command
            # Executing from self.ansible_dir, so ansible.cfg is picked up
            # ansible.cfg already defines vault_password_file = .vault_pass
            cmd = f"ansible-playbook -i {inventory_file} {playbook_path}"
            
            # Running from ansible_dir
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
