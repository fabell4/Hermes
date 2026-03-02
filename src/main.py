"""Hermes entry point — wires services, exporters, dispatcher, and web server together."""
from src.services.speedtest_runner import SpeedtestRunner


def main() -> None:
    """Run a speed test and display the results."""
    print("Running speed test...\n")
    result = SpeedtestRunner().run()
    print(f"Server   : {result.server_name} ({result.server_location})")
    print(f"Ping     : {result.ping_ms} ms")
    print(f"Download : {result.download_mbps} Mbps")
    print(f"Upload   : {result.upload_mbps} Mbps")


if __name__ == "__main__":
    main()
