# NordVPN CLI for macOS

A Python CLI tool for controlling NordVPN programmatically via Tunnelblick on macOS.

## Why Tunnelblick?

This tool uses Tunnelblick (OpenVPN client) with AppleScript for VPN control. This approach:

- **No sudo required** - Clean AppleScript API
- **Reliable macOS integration** - Battle-tested OpenVPN client
- **Simple automation** - Easy to script and automate

## Prerequisites

### 1. Install Tunnelblick

```bash
brew install --cask tunnelblick
```

### 2. Get NordVPN Service Credentials

1. Go to https://my.nordaccount.com/dashboard/nordvpn/manual-configuration/
2. Generate service credentials (NOT your login credentials)
3. Save the username and password

## Installation

```bash
git clone https://github.com/RobGruhl/hello-nordvpn.git
cd hello-nordvpn
poetry install
```

## Configuration

Create a `.env` file with your NordVPN service credentials:

```bash
cp .env.example .env
# Edit .env with your credentials
```

```
NORD_USER=your_service_username
NORD_PASS=your_service_password
```

## Usage

### Setup Wizard

Run the setup wizard to verify everything is configured:

```bash
poetry run nordvpn setup
```

### Basic Commands

```bash
# Check connection status
poetry run nordvpn status

# List available countries
poetry run nordvpn countries

# List servers in a country
poetry run nordvpn servers --country US
poetry run nordvpn servers -c DE --limit 20

# Connect to optimal server in a country
poetry run nordvpn connect --country US
poetry run nordvpn connect -c UK --city London

# Connect to specific server
poetry run nordvpn connect --server us5090.nordvpn.com

# Disconnect
poetry run nordvpn disconnect

# List installed configurations
poetry run nordvpn configs
```

### Example Output

```bash
$ poetry run nordvpn status
Connected to us5090.nordvpn.com
  Location: Seattle
  Server Load: 16%
  Public IP: 84.17.41.150

$ poetry run nordvpn servers -c US --limit 5
╭────────────────────────────────────────────────────────────────╮
│                  NordVPN Servers - United States               │
├────────────────────────┬─────────────┬───────┬────────────────┤
│ Hostname               │ City        │  Load │ Status         │
├────────────────────────┼─────────────┼───────┼────────────────┤
│ us5090.nordvpn.com     │ Seattle     │   12% │ online         │
│ us5091.nordvpn.com     │ Seattle     │   14% │ online         │
│ us4522.nordvpn.com     │ Los Angeles │   18% │ online         │
│ us8734.nordvpn.com     │ New York    │   21% │ online         │
│ us6721.nordvpn.com     │ Chicago     │   25% │ online         │
╰────────────────────────┴─────────────┴───────┴────────────────╯
```

## How It Works

1. **Server Discovery**: Uses NordVPN's public API to find optimal servers based on load and location
2. **Config Management**: Downloads OpenVPN configs on-demand and packages them for Tunnelblick
3. **VPN Control**: Uses AppleScript to control Tunnelblick (connect/disconnect)
4. **Status Detection**: Combines Tunnelblick status with IP geolocation for comprehensive status

## Architecture

```
nordvpn/
├── api/
│   ├── client.py         # NordVPN API client (async httpx)
│   └── models.py         # Pydantic models for API responses
├── vpn/
│   ├── tunnelblick.py    # AppleScript control for Tunnelblick
│   ├── config_manager.py # OpenVPN config download/packaging
│   └── status.py         # Connection status detection
├── utils/
│   └── credentials.py    # Environment-based credential loading
├── cli.py                # Typer CLI commands
└── __main__.py           # Entry point
```

## Troubleshooting

### Tunnelblick Prompts

On first connection to a new server, Tunnelblick may prompt:
- To install its helper tool (one-time)
- To confirm connecting to the new configuration

### Connection Timing

The `connect` command waits up to 30 seconds for the connection to establish. If this times out, the connection may still succeed shortly after.

### Config Names

Tunnelblick configurations are named like `us5090.nordvpn.com.udp`. The `.udp` suffix indicates UDP protocol (preferred for speed).

### Credentials Not Working

Ensure you're using **service credentials** from the manual configuration page, not your NordVPN login credentials. They are different.

## Use from Claude Code

All commands can be invoked via Bash:

```bash
# Check status
poetry run nordvpn status

# Connect
poetry run nordvpn connect -c US

# Disconnect
poetry run nordvpn disconnect
```
