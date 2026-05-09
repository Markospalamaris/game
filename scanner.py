#!/usr/bin/env python3
"""
Network + BLE Scanner
Scans the local network for devices and nearby Bluetooth Low Energy (BLE) devices.
"""

import subprocess
import socket
import threading
import ipaddress
import platform
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed

# Optional BLE support
try:
    import asyncio
    from bleak import BleakScanner
    BLE_AVAILABLE = True
except ImportError:
    BLE_AVAILABLE = False


def get_local_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        return s.getsockname()[0]
    finally:
        s.close()


def get_network_cidr(local_ip):
    parts = local_ip.split(".")
    return f"{parts[0]}.{parts[1]}.{parts[2]}.0/24"


def ping(ip):
    param = "-n" if platform.system().lower() == "windows" else "-c"
    try:
        result = subprocess.run(
            ["ping", param, "1", "-W", "1", str(ip)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=2,
        )
        return result.returncode == 0
    except Exception:
        return False


def resolve_hostname(ip):
    try:
        return socket.gethostbyaddr(str(ip))[0]
    except Exception:
        return "unknown"


def get_mac(ip):
    try:
        output = subprocess.check_output(["arp", "-n", str(ip)], stderr=subprocess.DEVNULL).decode()
        for line in output.splitlines():
            if str(ip) in line:
                parts = line.split()
                for part in parts:
                    if ":" in part and len(part) == 17:
                        return part
    except Exception:
        pass
    return "unknown"


def scan_host(ip):
    if ping(ip):
        hostname = resolve_hostname(ip)
        mac = get_mac(ip)
        return {"ip": str(ip), "hostname": hostname, "mac": mac}
    return None


def scan_network():
    local_ip = get_local_ip()
    network = get_network_cidr(local_ip)
    print(f"\n[*] Local IP   : {local_ip}")
    print(f"[*] Scanning   : {network}")
    print(f"[*] Please wait...\n")

    hosts = list(ipaddress.ip_network(network, strict=False).hosts())
    found = []

    with ThreadPoolExecutor(max_workers=50) as executor:
        futures = {executor.submit(scan_host, ip): ip for ip in hosts}
        for future in as_completed(futures):
            result = future.result()
            if result:
                found.append(result)
                print(f"  [+] {result['ip']:<18} {result['hostname']:<35} MAC: {result['mac']}")

    if not found:
        print("  No devices found.")

    print(f"\n[*] Scan complete. {len(found)} device(s) found.")
    return found


async def scan_ble():
    print("\n[*] Scanning for BLE devices (10 seconds)...\n")
    devices = await BleakScanner.discover(timeout=10.0)
    if not devices:
        print("  No BLE devices found.")
    else:
        for d in devices:
            print(f"  [+] {d.address:<20} RSSI: {d.rssi:<6} Name: {d.name or 'unknown'}")
    print(f"\n[*] BLE scan complete. {len(devices)} device(s) found.")


def main():
    print("=" * 60)
    print("       PC NETWORK + BLE SCANNER")
    print("=" * 60)

    # LAN scan
    scan_network()

    # BLE scan
    if BLE_AVAILABLE:
        asyncio.run(scan_ble())
    else:
        print("\n[!] BLE scanning unavailable. Install bleak: pip install bleak")

    print("\n" + "=" * 60)


if __name__ == "__main__":
    main()
