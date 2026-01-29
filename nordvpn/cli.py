"""CLI commands for NordVPN control."""

import asyncio
from typing import Annotated

import typer
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn

from .api import NordVPNClient
from .vpn import TunnelblickController, ConfigManager, get_connection_status
from .vpn.tunnelblick import ConnectionState, TunnelblickError
from .utils import get_credentials, Credentials
from .utils.credentials import CredentialsError

app = typer.Typer(
    name="nordvpn",
    help="Control NordVPN via Tunnelblick on macOS",
    no_args_is_help=True,
)
console = Console()


def _ensure_tunnelblick() -> None:
    """Ensure Tunnelblick is installed and running."""
    if not TunnelblickController.is_installed():
        console.print(
            "[red]Tunnelblick is not installed.[/red]\n"
            "Install with: brew install --cask tunnelblick"
        )
        raise typer.Exit(1)

    if not TunnelblickController.is_running():
        console.print("[yellow]Starting Tunnelblick...[/yellow]")
        TunnelblickController.launch()


def _run_async(coro):
    """Run an async function synchronously."""
    return asyncio.run(coro)


@app.command()
def status():
    """Show current VPN connection status."""
    _ensure_tunnelblick()

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
        transient=True,
    ) as progress:
        progress.add_task("Checking connection status...", total=None)
        conn_status = _run_async(get_connection_status())

    if conn_status.connected:
        console.print(f"[green]Connected[/green] to [bold]{conn_status.server_hostname}[/bold]")
        if conn_status.city or conn_status.country:
            location = conn_status.city or conn_status.country
            console.print(f"  Location: {location}")
        if conn_status.load is not None:
            console.print(f"  Server Load: {conn_status.load}%")
        if conn_status.public_ip:
            console.print(f"  Public IP: {conn_status.public_ip}")
    else:
        console.print("[yellow]Disconnected[/yellow]")


@app.command()
def connect(
    country: Annotated[
        str | None,
        typer.Option("--country", "-c", help="Two-letter country code (e.g., US, UK, DE)")
    ] = None,
    city: Annotated[
        str | None,
        typer.Option("--city", help="City name for more specific server selection")
    ] = None,
    server: Annotated[
        str | None,
        typer.Option("--server", "-s", help="Specific server hostname (e.g., us5090.nordvpn.com)")
    ] = None,
):
    """Connect to NordVPN.

    Either specify --server for a specific server, or --country (and optionally --city)
    for automatic optimal server selection.
    """
    _ensure_tunnelblick()

    if not server and not country:
        console.print("[red]Specify either --country or --server[/red]")
        raise typer.Exit(1)

    try:
        creds = get_credentials()
    except CredentialsError as e:
        console.print(f"[red]{e}[/red]")
        raise typer.Exit(1)

    async def do_connect():
        client = NordVPNClient()
        config_manager = ConfigManager()

        # Determine which server to connect to
        if server:
            hostname = server
            if not hostname.endswith(".nordvpn.com"):
                hostname = f"{hostname}.nordvpn.com"
            console.print(f"Connecting to [bold]{hostname}[/bold]...")
        else:
            # Find optimal server
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console,
                transient=True,
            ) as progress:
                progress.add_task(f"Finding optimal server in {country.upper()}...", total=None)
                optimal = await client.find_optimal_server(country, city=city)

            if not optimal:
                console.print(f"[red]No servers found for {country.upper()}[/red]")
                return False

            hostname = optimal.hostname
            city_name = optimal.city.name if optimal.city else ""
            console.print(
                f"Selected [bold]{hostname}[/bold] "
                f"({city_name or optimal.country.name if optimal.country else 'Unknown'}) "
                f"- Load: {optimal.load}%"
            )

        # Check if config is already installed
        config_name = f"{hostname}.udp"
        installed_configs = TunnelblickController.list_configs()

        if config_name not in installed_configs:
            console.print(f"[yellow]Installing configuration for {hostname}...[/yellow]")
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console,
                transient=True,
            ) as progress:
                progress.add_task("Downloading and installing config...", total=None)
                config_name = await config_manager.setup_server(
                    hostname, creds.username, creds.password
                )

            # Wait for Tunnelblick to register the new config
            console.print("[yellow]Waiting for Tunnelblick to register config...[/yellow]")
            await asyncio.sleep(3)

        # Connect
        console.print(f"[yellow]Connecting to {config_name}...[/yellow]")
        try:
            success = TunnelblickController.connect(config_name, wait=True, timeout=30)
        except TunnelblickError as e:
            console.print(f"[red]{e}[/red]")
            return False

        if success:
            console.print(f"[green]Connected to {hostname}[/green]")
            # Show IP after connection
            conn_status = await get_connection_status()
            if conn_status.public_ip:
                console.print(f"  Public IP: {conn_status.public_ip}")
            return True
        else:
            console.print("[red]Connection failed or timed out[/red]")
            return False

    success = _run_async(do_connect())
    if not success:
        raise typer.Exit(1)


@app.command()
def disconnect():
    """Disconnect from VPN."""
    _ensure_tunnelblick()

    tb_status = TunnelblickController.get_status()
    if tb_status.state == ConnectionState.DISCONNECTED:
        console.print("[yellow]Already disconnected[/yellow]")
        return

    console.print(f"Disconnecting from {tb_status.config_name}...")
    try:
        TunnelblickController.disconnect()
        console.print("[green]Disconnected[/green]")
    except TunnelblickError as e:
        console.print(f"[red]{e}[/red]")
        raise typer.Exit(1)


@app.command()
def servers(
    country: Annotated[
        str,
        typer.Option("--country", "-c", help="Two-letter country code")
    ],
    limit: Annotated[
        int,
        typer.Option("--limit", "-l", help="Maximum servers to show")
    ] = 10,
):
    """List available servers for a country."""

    async def list_servers():
        client = NordVPNClient()

        # Get country ID
        country_obj = await client.get_country_by_code(country)
        if not country_obj:
            console.print(f"[red]Country '{country}' not found[/red]")
            return

        # Get recommendations (already sorted by performance)
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
            transient=True,
        ) as progress:
            progress.add_task(f"Fetching servers for {country_obj.name}...", total=None)
            servers = await client.get_recommendations(country_id=country_obj.id, limit=limit)

        if not servers:
            console.print(f"[yellow]No servers found for {country_obj.name}[/yellow]")
            return

        table = Table(title=f"NordVPN Servers - {country_obj.name}")
        table.add_column("Hostname", style="cyan")
        table.add_column("City", style="green")
        table.add_column("Load", justify="right")
        table.add_column("Status")

        for server in servers:
            city = server.city.name if server.city else "-"
            load_style = "green" if server.load < 30 else "yellow" if server.load < 70 else "red"
            table.add_row(
                server.hostname,
                city,
                f"[{load_style}]{server.load}%[/{load_style}]",
                server.status,
            )

        console.print(table)

    _run_async(list_servers())


@app.command()
def countries():
    """List all available countries."""

    async def list_countries():
        client = NordVPNClient()

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
            transient=True,
        ) as progress:
            progress.add_task("Fetching countries...", total=None)
            countries_list = await client.get_countries()

        # Sort by name
        countries_list.sort(key=lambda c: c.name)

        table = Table(title="Available Countries")
        table.add_column("Code", style="cyan", width=6)
        table.add_column("Name", style="green")

        for country in countries_list:
            table.add_row(country.code.upper(), country.name)

        console.print(table)
        console.print(f"\n[dim]Total: {len(countries_list)} countries[/dim]")

    _run_async(list_countries())


@app.command()
def setup():
    """Setup wizard for first-time configuration."""
    console.print("[bold]NordVPN Setup Wizard[/bold]\n")

    # Check Tunnelblick
    console.print("Checking Tunnelblick...")
    if not TunnelblickController.is_installed():
        console.print(
            "[red]Tunnelblick is not installed.[/red]\n"
            "Install with: [bold]brew install --cask tunnelblick[/bold]"
        )
        raise typer.Exit(1)
    console.print("[green]✓[/green] Tunnelblick is installed")

    if not TunnelblickController.is_running():
        console.print("[yellow]Starting Tunnelblick...[/yellow]")
        TunnelblickController.launch()
    console.print("[green]✓[/green] Tunnelblick is running")

    # Check credentials
    console.print("\nChecking credentials...")
    try:
        creds = get_credentials()
        console.print("[green]✓[/green] Credentials configured")
    except CredentialsError:
        console.print(
            "[yellow]![/yellow] Credentials not configured\n\n"
            "Create a [bold].env[/bold] file with:\n"
            "  NORD_USER=your_service_username\n"
            "  NORD_PASS=your_service_password\n\n"
            "Get service credentials from:\n"
            "  https://my.nordaccount.com/dashboard/nordvpn/manual-configuration/"
        )
        raise typer.Exit(1)

    # Test API
    console.print("\nTesting NordVPN API...")

    async def test_api():
        client = NordVPNClient()
        try:
            countries = await client.get_countries()
            console.print(f"[green]✓[/green] API working ({len(countries)} countries available)")
            return True
        except Exception as e:
            console.print(f"[red]✗[/red] API error: {e}")
            return False

    if not _run_async(test_api()):
        raise typer.Exit(1)

    console.print("\n[green]Setup complete![/green]")
    console.print("\nTry these commands:")
    console.print("  [bold]nordvpn countries[/bold]      - List available countries")
    console.print("  [bold]nordvpn servers -c US[/bold]  - List US servers")
    console.print("  [bold]nordvpn connect -c US[/bold]  - Connect to optimal US server")
    console.print("  [bold]nordvpn status[/bold]         - Check connection status")
    console.print("  [bold]nordvpn disconnect[/bold]     - Disconnect from VPN")


@app.command()
def configs():
    """List installed Tunnelblick configurations."""
    _ensure_tunnelblick()

    configs = TunnelblickController.list_configs()

    if not configs:
        console.print("[yellow]No NordVPN configurations installed[/yellow]")
        return

    # Filter to NordVPN configs
    nord_configs = [c for c in configs if "nordvpn" in c.lower()]

    if not nord_configs:
        console.print("[yellow]No NordVPN configurations installed[/yellow]")
        return

    console.print(f"[bold]Installed NordVPN Configurations ({len(nord_configs)}):[/bold]")
    for config in sorted(nord_configs):
        console.print(f"  • {config}")
