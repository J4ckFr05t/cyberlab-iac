First: The Easiest Way to Keep Paperclip Running on Boot
Before creating your company, note two critical details from the latest Paperclip documentation for your Ubuntu server setup:

Do NOT run as root: Paperclip uses an embedded PostgreSQL database by default, which refuses to start as root. Always run it under a normal user (e.g., ubuntu or a dedicated paperclip user created via sudo adduser paperclip).

Use Paperclip's built-in service installer (Node.js 24.11+ required): Instead of writing a manual systemd file, Paperclip has a native command that installs itself and registers a background service that starts on boot and auto-restarts on crashes:

Bash
# 1. Install Node.js 24 LTS (if not already on v24.11+)
curl -fsSL https://deb.nodesource.com/setup_24.x | sudo -E bash -
sudo apt install -y nodejs

# 2. Switch to your non-root user and run the managed installer
npx paperclipai install

# 3. Initialize the database and default config headless
paperclipai onboard --yes

# 4. Register Paperclip as an always-on background service
paperclipai service install
Verify it is running: Run paperclipai service status or paperclipai doctor to confirm the service is healthy and listening on port 3100.

3 Ways to Create a Company & Setup Agents from the Terminal
Once your server is running in the background, you can configure everything from your SSH session:

1. Using the paperclipai CLI
Paperclip's CLI maps directly to its control plane. You can create a company, set its goal, and manage agents straight from bash:

Bash
# Create a new company with an initial mission/goal
paperclipai company create --name "Acme AI" --goal "Build and maintain our automated backend services"

# List your companies and grab the Company ID
paperclipai company list
You can also manage the rest of your organization using the CLI subcommands (add --help to any command to see all flags):

paperclipai agent ... — Hire, configure, pause, or list agents (e.g., your CEO agent).

paperclipai goal ... — Add or update company and project goals.

paperclipai project ... — Create projects and link execution workspaces/repos.

paperclipai issue ... — Create and assign tasks/tickets from the terminal.

paperclipai secret ... — Store your AI provider API keys (OPENAI_API_KEY, ANTHROPIC_API_KEY, etc.).

2. Importing a Pre-Built Company Template (Fastest CLI Setup)
Instead of configuring a CEO, org chart, and skills one by one, Paperclip has an official repository (paperclipai/companies) of pre-packaged company structures that you can pull and import via terminal:

Bash
# Download the default starter company (includes baseline CEO & roles)
# Or use templates like: paperclipai/companies/gstack or paperclipai/companies/superpowers
npx companies.sh add paperclipai/companies/default

# Preview the import (dry run)
paperclipai company import ./default --dry-run

# Import the company into your running Paperclip server
paperclipai company import ./default
3. Using the REST API (curl)
Because Paperclip runs a local Express REST API on http://localhost:3100, you can script your entire company creation using curl:

Bash
# 1. Create a company
curl -s -X POST http://localhost:3100/api/companies \
  -H "Content-Type: application/json" \
  -d '{
    "name": "My Autonomous Co",
    "issuePrefix": "MAC"
  }' | jq

# 2. List existing companies to get your companyId
curl -s http://localhost:3100/api/companies | jq

# 3. Add a secret (e.g., Anthropic or OpenAI API key) to the company
curl -s -X POST http://localhost:3100/api/companies/<COMPANY_ID>/secrets \
  -H "Content-Type: application/json" \
  -d '{
    "name": "ANTHROPIC_API_KEY",
    "value": "sk-ant-..."
  }'

# 4. Create your first Goal
curl -s -X POST http://localhost:3100/api/companies/<COMPANY_ID>/goals \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Launch MVP",
    "description": "Design, build, and test the v1 web service."
  }'

FrostSec AI SOC — Paperclip Initial Organization & Ansible Bootstrap Specification

1. Purpose

Build the initial FrostSec AI SOC organization in Paperclip and prepare the environment so an AI agent can generate the required Ansible automation.

This is a small-resource cybersecurity research lab. The design must prioritize low resource consumption, simplicity, isolation, reproducibility, and gradual expansion.

The existing lab has:



One Windows 11 workstation

One Ubuntu workstation

A Proxmox-based lab environment

Existing network segmentation and infrastructure-as-code

Limited CPU/RAM resources

Do not introduce large infrastructure such as Kubernetes, Kafka, Elasticsearch/OpenSearch, Wazuh, or additional heavyweight VMs unless explicitly requested later.





2. Company

Company name

FrostSec Security Operations



Company type

Cybersecurity research and security operations organization.



Mission

Build a controlled autonomous security operations capability that continuously monitors a simulated enterprise environment, investigates suspicious activity, performs threat hunting, develops detections, coordinates incident response, consumes threat intelligence, and continuously improves its defensive capabilities.

Primary functions

Security Operations

Threat Hunting

Incident Response

Detection Engineering

Threat Intelligence

Security Automation

Environment

This is a controlled cybersecurity research laboratory. All endpoints, telemetry, credentials, attack simulations, and security testing must remain inside the authorized lab environment.





3. Resource Philosophy

The Paperclip server is intentionally lightweight.

Initial Paperclip VM target:

ResourceTargetvCPU2RAM4 GBDisk50 GB SSDOSUbuntu Server 24.04 LTSGPUNone

The AI models are expected to run through external model providers/runtimes rather than locally on the Paperclip VM.

The automation must therefore avoid unnecessary resource consumption.



Requirements

Prefer native Ubuntu packages where appropriate.

Prefer Docker/Compose only where Paperclip's installation requires it.

Do not install a local LLM.

Do not install a GPU stack.

Do not install a full SIEM.

Do not install heavyweight databases unless required by the installed Paperclip version.

Do not expose Paperclip directly to the public Internet.

Keep management access restricted to the lab management network/VPN.

Make all configuration reproducible through Ansible.





4. AI Employee Organization

Use human-readable professional names, not fantasy/sci-fi names.

The CEO should be named:

Morgan

The name is intentionally generic and professional. Avoid names such as Frost, Sentinel, Jarvis, Skynet, CyberBot, etc.



Organization

FrostSec Security Operations

│

├── Executive Office

│ └── Morgan — Chief Executive Officer

│

├── Security Operations

│ ├── Alex — SOC Director

│ ├── Sam — Security Operations Analyst

│ ├── Jordan — Threat Hunter

│ └── Riley — Incident Response Analyst

│

├── Security Engineering

│ └── Taylor — Detection & Security Engineer

│

└── Threat Intelligence

└── Casey — Threat Intelligence Analyst

Total initial AI employees: 7





5. Employee Definitions

5.1 Morgan

Title

Chief Executive Officer



Role

CEO / Executive Security Decision Maker



Reports to

Nobody



Mission

Own the overall FrostSec security mission, establish priorities, evaluate risk, coordinate the organization, approve major security initiatives, and ensure security activities contribute to the company's mission.



Responsibilities

Establish security priorities.

Review major incidents.

Review strategic threat intelligence.

Resolve conflicts between teams.

Approve major security initiatives.

Ensure investigations result in actionable outcomes.

Coordinate the SOC, security engineering, and threat intelligence functions.

Capabilities

Cybersecurity strategy

Security operations

Risk assessment

Incident prioritization

Threat intelligence

Security architecture

Decision making

AI-agent coordination

Operating principle

Morgan should not perform routine alert triage or individual investigations. Morgan is the strategic decision layer.





5.2 Alex

Title

SOC Director



Role

Security Operations Manager



Reports to

Morgan



Mission

Manage day-to-day security operations and coordinate investigations across the SOC.



Responsibilities

Prioritize alerts and incidents.

Delegate investigations.

Coordinate SOC analysts.

Coordinate threat hunting and incident response.

Review investigation findings.

Escalate significant incidents to Morgan.

Ensure incidents progress to actionable conclusions.

Capabilities

SOC operations

Alert triage

Incident coordination

Security monitoring

Threat detection

Investigation management

MITRE ATT&CK

Incident prioritization





5.3 Sam

Title

Security Operations Analyst



Role

SOC Analyst



Reports to

Alex



Mission

Monitor security telemetry, triage alerts, investigate suspicious activity, correlate events, gather evidence, and escalate confirmed threats.



Responsibilities

Analyze Windows telemetry.

Analyze Linux telemetry.

Investigate authentication events.

Investigate suspicious processes.

Analyze endpoint activity.

Analyze IOCs.

Correlate related events.

Escalate high-confidence threats.

Capabilities

Log analysis

Alert triage

Endpoint telemetry

Windows security events

Linux logs

Authentication analysis

Process analysis

Network telemetry

IOC analysis

MITRE ATT&CK





5.4 Jordan

Title

Threat Hunter



Role

Threat Hunter / Security Analyst



Reports to

Alex



Mission

Proactively identify malicious behavior that may not be detected by existing security controls.



Responsibilities

Develop threat-hunting hypotheses.

Search endpoint telemetry.

Search authentication activity.

Investigate persistence mechanisms.

Investigate lateral movement.

Investigate credential abuse.

Search for ATT&CK techniques.

Recommend new detections.

Capabilities

Threat hunting

MITRE ATT&CK

Detection hypothesis development

Windows internals

Linux security

PowerShell

Bash

Process analysis

Persistence detection

Lateral movement

Credential abuse

IOC hunting





5.5 Riley

Title

Incident Response Analyst



Role

Incident Responder



Reports to

Alex



Mission

Investigate confirmed security incidents, determine scope and impact, establish timelines, recommend containment, and document lessons learned.



Responsibilities

Investigate confirmed incidents.

Establish attack timelines.

Determine affected hosts.

Determine affected accounts.

Analyze evidence.

Recommend containment.

Recommend eradication.

Recommend recovery.

Produce incident reports.

Perform root-cause analysis.

Capabilities

Incident response

Digital forensics

Timeline analysis

Windows forensics

Linux forensics

Evidence analysis

Containment

Eradication

Recovery

Root-cause analysis

Incident documentation





5.6 Taylor

Title

Detection & Security Engineer



Role

Detection Engineer



Reports to

Morgan



Mission

Develop, test, tune, and maintain security detections based on observed threats, threat intelligence, attack techniques, and investigation findings.



Responsibilities

Develop detections.

Translate ATT&CK techniques into detection logic.

Develop Sigma rules where appropriate.

Develop Python-based detection utilities.

Develop SQL-based analytics where appropriate.

Tune false positives.

Validate detections against lab telemetry.

Document detection coverage.

Collaborate with Threat Hunting and SOC teams.

Capabilities

Detection engineering

Sigma

YARA

Python

SQL

Log analytics

MITRE ATT&CK

Detection tuning

False-positive analysis

Security automation

Threat research





5.7 Casey

Title

Threat Intelligence Analyst



Role

Threat Intelligence Analyst



Reports to

Morgan



Mission

Collect, analyze, contextualize, and operationalize threat intelligence for the SOC, threat hunting, detection engineering, and incident response teams.



Responsibilities

Research threat actors.

Analyze IOCs.

Analyze TTPs.

Research malware.

Research CVEs.

Monitor KEV-related vulnerabilities.

Map intelligence to MITRE ATT&CK.

Produce intelligence summaries.

Provide intelligence to detection engineering.

Provide intelligence to threat hunting.

Capabilities

Threat intelligence

IOC analysis

TTP analysis

MITRE ATT&CK

Threat actor research

Malware research

Vulnerability intelligence

CVE analysis

KEV analysis

OSINT

Threat-report analysis





6. Reporting Relationships

The reporting structure must be:



Morgan

│

├── Alex

│ ├── Sam

│ ├── Jordan

│ └── Riley

│

├── Taylor

│

└── Casey

Do not create additional managers initially.





7. Security Workflow

The organization should support this workflow:



Telemetry

|

v

Sam - SOC Analyst

|

| suspicious activity

v

Alex - SOC Director

|

+------------------+

| |

v v

Jordan Riley

Threat Hunter Incident Response

| |

+--------+---------+

|

v

Investigation

|

v

Taylor

Detection Engineering

|

v

Improved Detection

|

v

Sam

Threat intelligence should feed multiple functions:



Casey - Threat Intelligence

|

+----> Sam

|

+----> Jordan

|

+----> Taylor

|

+----> Riley

Strategic decisions and major incidents escalate to:



Alex / Taylor / Casey

|

v

Morgan





8. Initial Agent Activation Strategy

Do not activate all agents aggressively at the beginning.

Initial phase:



Morgan

|

v

Alex

|

v

Sam

After basic telemetry and integrations work:



Jordan

Taylor

Riley

Casey

The reason is resource and cost control.

Agents should not continuously wake up when there is no meaningful work.

Avoid autonomous polling loops unless there is a concrete data source and task.





9. Lab Infrastructure

Existing endpoints:



Windows 11 workstation

Ubuntu workstation

The AI SOC should treat these as the initial enterprise endpoints.

The Paperclip VM should act as the control/orchestration plane.

Conceptually:



FrostSec

|

Morgan

|

Alex

|

+---------+---------+

| |

SOC Security

| Engineering

| |

Sam Taylor

|

+-------+-------+

| |

Windows Ubuntu

endpoint endpoint

Threat intelligence and threat hunting should operate across the available telemetry.





10. Ansible Requirements

The generated Ansible automation should be idempotent.

It must be safe to execute multiple times.



Suggested Ansible structure

ansible/

├── inventory/

│ └── hosts.yml

├── group_vars/

│ └── all.yml

├── playbooks/

│ ├── paperclip.yml

│ └── security-baseline.yml

├── roles/

│ ├── common/

│ ├── paperclip/

│ └── security-baseline/

└── templates/

The exact structure may be simplified if the existing lab repository already has an established Ansible structure.

Do not create a second conflicting infrastructure structure.





11. Paperclip VM Ansible Tasks

The Paperclip role should perform only necessary tasks.



Base configuration

Update package metadata.

Install required system packages.

Configure timezone.

Configure hostname.

Configure basic security settings.

Create a dedicated Paperclip service user if required.

Configure required directories.

Configure ownership and permissions.

Paperclip

Install the Paperclip version specified by the lab.

Configure Paperclip using environment variables/configuration files as supported by the installed version.

Configure its database/storage according to the official installation requirements.

Configure the Paperclip service.

Enable service startup.

Start the service.

Verify health after startup.

Do not hard-code credentials.

Use Ansible Vault for secrets.





12. Network Security

Paperclip must not be publicly exposed.

Recommended model:



Internet

X

|

VPN / Management Network

|

Paperclip

|

Lab Network

|

+-- Windows 11

|

+-- Ubuntu

Firewall rules should allow only required traffic.

At minimum:



SSH from the management network.

Paperclip web/API access from the management network.

Required outbound HTTPS for model/API integrations.

Required communication to explicitly configured lab services.

Deny unnecessary inbound traffic.

Do not blindly open all ports.





13. Secrets

Never put these directly into Git:



API keys

OAuth tokens

Passwords

SSH private keys

Paperclip authentication secrets

Cloud credentials

GitHub tokens

Model-provider API keys

Use:



Ansible Vault

or another existing secret-management mechanism already present in the lab.

Provide a .example configuration containing variable names but no real secrets.





14. Security Baseline

The Ansible role should implement a reasonable Ubuntu baseline without making the lab difficult to operate.

Potential tasks:



Disable unnecessary services.

Configure UFW or the lab's existing firewall mechanism.

Configure SSH securely.

Disable password SSH authentication if key-based authentication is already available.

Disable root SSH login.

Configure unattended security updates only if compatible with the lab's existing maintenance model.

Set correct filesystem permissions.

Create dedicated service users.

Enable basic system logging.

Do not make destructive changes to existing lab networking or Proxmox configuration.





15. Agent Configuration Requirements

When creating Paperclip agents, configure:



Name

Role

Title

Reporting manager

Capabilities

Agent purpose

Operating instructions

Appropriate execution adapter

Appropriate model/runtime

Reasonable budget

Appropriate heartbeat/scheduling configuration

Avoid assigning excessive budgets.

The AI agents should use the minimum privileges required for their tasks.





16. Agent Security Model

Agents must follow these principles:



Default deny

An agent should not automatically receive:



Root access

Proxmox administration

Arbitrary Internet access

Production credentials

Personal credentials

Unrestricted GitHub write access

Unrestricted endpoint command execution

Investigation versus action

The initial agents should primarily:



Observe

↓

Analyze

↓

Recommend

↓

Request approval

↓

Execute

Do not start with:



Observe

↓

Automatically execute anything

For destructive or disruptive actions such as:



Host isolation

Account disabling

File deletion

Process termination

Firewall modification

Credential rotation

require explicit authorization during the initial lab phase.





17. Auditability

Every agent action should be traceable.

Record:



Agent

Task

Input

Decision

Tool used

Command executed

Result

Timestamp

Final recommendation

Approval, if required

The objective is to make the AI SOC explainable and auditable.





18. Initial SOC Scenarios

The lab should eventually support scenarios such as:



Suspicious PowerShell execution

Brute-force authentication

Suspicious Linux authentication

Privilege escalation

Persistence

Suspicious scheduled task

Suspicious process execution

Credential abuse

Lateral movement

Malicious file execution

C2-like network behavior

Vulnerable endpoint discovery

Do not implement all scenarios in the first deployment.

Start with:



1. Suspicious PowerShell

2. Authentication anomaly

3. Suspicious Linux command execution





19. Detection Engineering Loop

The organization should eventually implement:



Threat Intelligence

|

v

Threat Hypothesis

|

v

Threat Hunting

|

v

Evidence

|

v

Detection Engineering

|

v

Detection Rule

|

v

Testing

|

v

SOC Deployment

|

v

Monitoring

|

v

False Positive Feedback

|

+-----------> Detection Engineering

This loop is one of the core objectives of the FrostSec AI SOC.





20. Ansible Validation

After deployment, Ansible should verify:



[ ] Paperclip service running

[ ] Paperclip reachable from management network

[ ] Paperclip NOT publicly reachable

[ ] Required ports listening

[ ] Required directories exist

[ ] Correct file ownership

[ ] Correct permissions

[ ] No plaintext secrets in configuration

[ ] Database/storage functioning

[ ] Paperclip health check succeeds

[ ] Agent configuration can be loaded

The playbook should fail clearly when a critical requirement is not satisfied.





21. Idempotency Requirements

Running:



ansible-playbook playbooks/paperclip.yml

multiple times must not:



Recreate users unnecessarily

Reset credentials

Duplicate configuration

Duplicate agents

Duplicate departments

Reinstall software unnecessarily

Destroy existing Paperclip data

Use Ansible modules rather than shell commands whenever possible.

If CLI commands are unavoidable, make them conditional and idempotent.





22. What the AI Building the Ansible Script Must NOT Do

Do not:



Invent Paperclip CLI parameters.

Assume a Paperclip version.

Hard-code secrets.

Hard-code external IP addresses.

Destroy existing lab infrastructure.

Modify Proxmox networking without explicit instructions.

Create unnecessary VMs.

Install heavyweight SIEM infrastructure.

Install local LLM infrastructure.

Expose Paperclip to the Internet.

Give all agents root access.

Automatically grant agents destructive endpoint capabilities.

Replace existing Terraform/Ansible architecture without inspecting it first.

Before generating the final automation, inspect:



paperclipai --version

paperclipai --help

paperclipai company --help

paperclipai agent --help

and inspect the existing lab repository structure.

The generated automation must match the installed Paperclip version and the existing lab's IaC conventions.





23. Desired End State

The initial deployment should produce:



FrostSec Security Operations

│

├── Executive Office

│ └── Morgan

│

├── Security Operations

│ ├── Alex

│ ├── Sam

│ ├── Jordan

│ └── Riley

│

├── Security Engineering

│ └── Taylor

│

└── Threat Intelligence

└── Casey

with:



Paperclip VM

|

+-- Company configured

+-- Departments configured

+-- 7 AI employees configured

+-- Reporting hierarchy configured

+-- Goals configured

+-- Agent capabilities configured

+-- Secure credentials configured

+-- Lab connectivity configured

+-- Auditability preserved

The deployment must remain lightweight enough to operate comfortably in a small personal cybersecurity lab.





24. Design Principle

The FrostSec AI SOC is not intended to be a collection of AI chatbots.

The intended architecture is:



┌──────────────┐

│ Morgan │

│ Strategy │

└──────┬───────┘

│

┌──────▼───────┐

│ Alex │

│ SOC Manager │

└──────┬───────┘

│

┌─────────────┼─────────────┐

│ │ │

▼ ▼ ▼

Sam Jordan Riley

SOC Hunt IR

│ │ │

└─────────────┼─────────────┘

│

▼

Taylor

Detection Eng.

▲

│

Casey

Threat Intel

The system should progressively evolve from:

AI-assisted SOC

to:

AI-coordinated SOC

while keeping human authorization and strong security boundaries around destructive actions.