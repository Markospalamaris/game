#!/usr/bin/env python3
"""
Network + BLE Scanner — iOS compatible (Pythonista 3 / a-Shell / iSH)
Uses only Python stdlib: no ping, no arp, no subprocess.
"""

import socket
import struct
import fcntl
import asyncio
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed

# BLE — only works on macOS/Linux with bleak installed
try:
    from bleak import BleakScanner
    BLE_AVAILABLE = True
except ImportError:
    BLE_AVAILABLE = False

# Pythonista-specific BLE (cb module)
try:
    import cb
    PYTHONISTA_BLE = True
except ImportError:
    PYTHONISTA_BLE = False


# ── Helpers ──────────────────────────────────────────────────────────────────

def get_local_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        return s.getsockname()[0]
    except Exception:
        return "127.0.0.1"
    finally:
        s.close()


def get_network_range(local_ip):
    """Returns list of all host IPs in the /24 subnet."""
    parts = local_ip.split(".")
    base = f"{parts[0]}.{parts[1]}.{parts[2]}."
    return [f"{base}{i}" for i in range(1, 255)]


def tcp_ping(ip, ports=(80, 443, 22, 8080, 139, 445), timeout=0.5):
    """Returns True if any common TCP port responds — no ping required."""
    for port in ports:
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(timeout)
            result = s.connect_ex((ip, port))
            s.close()
            if result == 0:
                return True
        except Exception:
            pass
    return False


def resolve_hostname(ip):
    try:
        return socket.gethostbyaddr(ip)[0]
    except Exception:
        return "unknown"


def scan_host(ip):
    if tcp_ping(ip):
        hostname = resolve_hostname(ip)
        return {"ip": ip, "hostname": hostname}
    return None


# ── LAN scan ─────────────────────────────────────────────────────────────────

def scan_network():
    local_ip = get_local_ip()
    hosts = get_network_range(local_ip)

    print(f"\n[*] Your IP    : {local_ip}")
    print(f"[*] Scanning   : {local_ip.rsplit('.', 1)[0]}.0/24")
    print(f"[*] Method     : TCP port probe (iOS compatible)")
    print(f"[*] Please wait...\n")

    found = []
    with ThreadPoolExecutor(max_workers=50) as executor:
        futures = {executor.submit(scan_host, ip): ip for ip in hosts}
        for future in as_completed(futures):
            result = future.result()
            if result:
                found.append(result)
                print(f"  [+] {result['ip']:<18} {result['hostname']}")

    if not found:
        print("  No devices found.")

    print(f"\n[*] Scan complete — {len(found)} device(s) found.")
    return found


# ── BLE scan ─────────────────────────────────────────────────────────────────

async def scan_ble_bleak():
    print("\n[*] Scanning BLE devices (10s)...\n")
    devices = await BleakScanner.discover(timeout=10.0)
    if not devices:
        print("  No BLE devices found.")
    else:
        for d in devices:
            print(f"  [+] {d.address:<20} RSSI: {d.rssi:<6} Name: {d.name or 'unknown'}")
    print(f"\n[*] BLE scan complete — {len(devices)} device(s) found.")


def scan_ble_pythonista():
    """CoreBluetooth BLE scan via Pythonista cb module."""
    import time

    found = {}

    class Delegate(cb.CentralManagerDelegate):
        def did_discover_peripheral(self, manager, peripheral, adv_data, rssi):
            addr = peripheral.uuid
            name = peripheral.name or adv_data.get("kCBAdvDataLocalName", "unknown")
            if addr not in found:
                found[addr] = (name, rssi)
                print(f"  [+] {addr:<36} RSSI: {rssi:<6} Name: {name}")

    print("\n[*] Scanning BLE devices via CoreBluetooth (10s)...\n")
    manager = cb.CentralManager(Delegate())
    time.sleep(10)
    manager.stop_scan()
    print(f"\n[*] BLE scan complete — {len(found)} device(s) found.")


# ── Entry point ───────────────────────────────────────────────────────────────

def main():
    print("=" * 55)
    print("       PC NETWORK + BLE SCANNER  (iOS Ready)")
    print("=" * 55)

    scan_network()

    if PYTHONISTA_BLE:
        scan_ble_pythonista()
    elif BLE_AVAILABLE:
        asyncio.run(scan_ble_bleak())
    else:
        print("\n[!] BLE unavailable.")
        print("    • On Pythonista 3: BLE works natively via cb module.")
        print("    • On desktop: pip install bleak")

    print("\n" + "=" * 55)


if __name__ == "__main__":
    main()
