# Network Skills

## DNS Configuration
- **Provider switching** — Switch between DNS providers (Cloudflare, Google, Quad9, custom)
- **DNS-over-HTTPS** — Configure encrypted DNS resolution
- **Split DNS** — Per-interface DNS configuration

**Modules:** `core/executor/operations.py` (NetworkOps)
**UI:** Network Tab
**CLI:** `network`

## Interface Management
- **Interface listing** — Enumerate all network interfaces with status
- **Connection control** — Connect/disconnect interfaces
- **IP configuration** — View and set IP addresses, routes, gateways

**UI:** Network Tab

## Network Monitoring
- **Traffic monitoring** — Real-time bandwidth usage per interface
- **Connectivity checks** — Verify internet, DNS, gateway reachability
- **Latency tracking** — Monitor ping times to configured targets

**Modules:** `utils/network_monitor.py`
**UI:** Network Tab
**CLI:** `netmon`

## Bluetooth Management
- **Device discovery** — Scan for nearby Bluetooth devices
- **Pairing** — Pair and trust Bluetooth devices
- **Connection management** — Connect/disconnect paired devices

**Modules:** `services/hardware/bluetooth.py`
**UI:** Hardware Tab
**CLI:** `bluetooth`

## Mesh Discovery (Loofi Link)
- **mDNS peer discovery** — Find other Loofi instances on the local network
- **LAN file transfer** — Send files to discovered peers
- **Clipboard sync** — Synchronize clipboard across connected devices

**Modules:** `utils/mesh_discovery.py`, `utils/clipboard_sync.py`, `utils/file_drop.py`
**UI:** Mesh Tab
**CLI:** `mesh`

## Wi-Fi Management
- **Network scanning** — Scan available Wi-Fi networks
- **Connection profiles** — Manage saved Wi-Fi connections
- **Security info** — Display encryption type and signal strength

**UI:** Network Tab

## VPN Support
- **VPN status** — Show active VPN connections
- **Connection management** — Connect/disconnect VPN profiles

**UI:** Network Tab
