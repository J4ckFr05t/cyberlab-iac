# Suricata Setup Role

This role installs and configures Suricata IDS on `SOC-01-SRV` and integrates it with the Wazuh Agent.

## Tasks

1.  **Installation**: Installs `suricata` and `net-tools` from the OISF stable PPA.
2.  **Configuration**:
    *   Configures `HOME_NET` to `[172.16.10.0/24]`.
    *   Configures `EXTERNAL_NET` to `any`.
    *   Enables global statistics.
    *   Sets `default-rule-path` to `/var/lib/suricata/rules`.
    *   Configures `rule-files` to load `suricata.rules`.
    *   Updates network interface in `af-packet` configuration.
3.  **Rules**:
    *   Runs `suricata-update` to download and bundle rules.
    *   Restarts Suricata service to apply changes.
4.  **Wazuh Integration**:
    *   Adds a `<localfile>` block to `/var/ossec/etc/ossec.conf` to ingest `/var/log/suricata/eve.json`.
    *   Restarts Wazuh Agent.

## Handlers

*   `restart suricata`: Restarts the Suricata service.
*   `restart wazuh-agent`: Restarts the Wazuh Agent service.
