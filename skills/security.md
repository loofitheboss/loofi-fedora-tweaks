# Security Skills

## Firewall Management

- **Zone management** — Create, modify, delete firewalld zones
- **Port rules** — Open/close ports with protocol specification
- **Rich rules** — Advanced firewall rules with source/destination filtering
- **Service rules** — Allow/deny services through firewall

**Modules:** `utils/firewall_manager.py`
**UI:** Security Tab
**CLI:** `firewall`

## SELinux

- **Mode management** — Switch between enforcing, permissive, disabled
- **Boolean toggles** — Enable/disable SELinux booleans
- **Audit review** — Review SELinux denials and generate policies

**UI:** Security Tab

## USB Guard

- **Device policy** — Allow/block USB devices by vendor/product ID
- **Whitelist management** — Maintain trusted USB device list
- **Real-time blocking** — Block unauthorized USB devices on connect

**Modules:** `utils/usbguard.py`
**UI:** Security Tab

## Security Audit

- **Security scoring** — Calculate system security posture score
- **Vulnerability check** — Identify common misconfigurations
- **Compliance review** — Check against security baselines
- **Audit log review** — Browse privilege escalation history

**Modules:** `utils/audit.py`, `utils/risk.py`
**UI:** Security Tab
**CLI:** `security-audit`, `audit-log`

## Secure Boot

- **Status check** — Verify Secure Boot enrollment state
- **Key management** — View enrolled keys and certificates

**Modules:** `utils/secureboot.py`
**UI:** System Info Tab

## Port Auditing

- **Open port scan** — Identify listening ports and associated processes
- **Service mapping** — Map ports to systemd services
- **Suspicious detection** — Flag unexpected listeners

**Modules:** `utils/ports.py`
**UI:** Security Tab

## Biometric Authentication

- **Fingerprint enrollment** — Register fingerprint for authentication
- **Fingerprint login** — Use fingerprint for privilege escalation

**Modules:** `utils/fingerprint.py`
**UI:** Security Tab

## Privilege Escalation

- **pkexec** — All root operations use Polkit-based escalation (never sudo)
- **Polkit policy** — Custom policy at `config/org.loofi.fedora-tweaks.policy`
- **Audit trail** — Every privileged action logged with timestamp, params, exit code

**Modules:** `utils/commands.py` (PrivilegedCommand), `utils/audit.py`
