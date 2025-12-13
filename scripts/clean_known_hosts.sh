#!/bin/bash

# Script to remove known_host entries for Lab Linux machines
# Use this when you redeploy VMs and SSH keys change

KNOWN_HOSTS_FILE="/home/jackfrost/.ssh/known_hosts"

# Linux Workstation
ssh-keygen -f "$KNOWN_HOSTS_FILE" -R '172.16.10.70'

# Infrastructure Servers
ssh-keygen -f "$KNOWN_HOSTS_FILE" -R '172.16.10.210'
ssh-keygen -f "$KNOWN_HOSTS_FILE" -R '172.16.10.220'
ssh-keygen -f "$KNOWN_HOSTS_FILE" -R '172.16.10.230'

echo "Known hosts cleaned for Lab Linux machines."