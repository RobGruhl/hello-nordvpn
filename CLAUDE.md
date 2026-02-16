# hello-nordvpn

Python CLI for controlling NordVPN programmatically via Tunnelblick (OpenVPN) on macOS. No sudo required.

## File Map

```
nordvpn/
  cli.py               — Typer CLI: connect, disconnect, status, servers, countries, configs, setup
  __main__.py           — Entry point (poetry run nordvpn)
  api/
    client.py           — Async NordVPN API client (httpx) — server discovery, recommendations
    models.py           — Pydantic models: Server, Country, City
  vpn/
    tunnelblick.py      — AppleScript control: connect/disconnect/status via Tunnelblick
    config_manager.py   — Downloads OpenVPN configs, packages as .tblk for Tunnelblick
    status.py           — Connection status: combines Tunnelblick state + IP geolocation
  utils/
    credentials.py      — Loads NORD_USER/NORD_PASS from .env
pyproject.toml          — Poetry config, deps: httpx, typer, pydantic, rich, python-dotenv
```

## CLI Commands

```bash
poetry run nordvpn setup                  # First-time wizard: checks Tunnelblick, creds, API
poetry run nordvpn status                 # Show connection state, server, IP, load
poetry run nordvpn connect -c US          # Connect to optimal server in country
poetry run nordvpn connect -c UK --city London  # Filter by city
poetry run nordvpn connect -s us5090.nordvpn.com  # Connect to specific server
poetry run nordvpn disconnect             # Disconnect current VPN
poetry run nordvpn countries              # List all available countries
poetry run nordvpn servers -c US          # List servers by country (sorted by load)
poetry run nordvpn configs                # List installed Tunnelblick configurations
```

## Key Gotchas

- **Requires Tunnelblick**: `brew install --cask tunnelblick` — must be installed and running
- **Service credentials, not login**: Get from https://my.nordaccount.com/dashboard/nordvpn/manual-configuration/ — these are separate from your NordVPN account password
- **AppleScript permissions**: macOS will prompt to allow automation of Tunnelblick on first use
- **First-connection prompts**: Tunnelblick may prompt to install helper tool and confirm new configs
- **30-second connect timeout**: `connect` waits up to 30s; connection may still succeed after timeout
- **Config naming**: Tunnelblick configs are named `{hostname}.udp` (e.g., `us5090.nordvpn.com.udp`)
- **Async internals**: API client uses httpx async, wrapped with `asyncio.run()` in CLI commands

## Copy to New Project

1. Copy `nordvpn/` directory
2. `poetry add httpx typer[all] pydantic python-dotenv rich`
3. Add to `.env`:
   ```
   NORD_USER=your_service_username
   NORD_PASS=your_service_password
   ```
4. Add to `pyproject.toml`:
   ```toml
   [tool.poetry.scripts]
   nordvpn = "nordvpn.__main__:main"
   ```
5. Run: `poetry run nordvpn setup`

## Architecture

1. **Server Discovery** — NordVPN public API returns servers sorted by load/location
2. **Config Management** — Downloads `.ovpn` files, bundles as `.tblk` with embedded credentials
3. **VPN Control** — AppleScript tells Tunnelblick to connect/disconnect specific configs
4. **Status Detection** — Reads Tunnelblick state + queries IP geolocation API for public IP
