# file_handler.py
"""
Handles reading CSV host files and individual JSON command files,
as well as saving results to XLSX.
"""

import csv
import json
import os

from openpyxl import Workbook
from datetime import datetime

def save_results(hosts, output_path):
    """Write results to XLSX."""
    try:
        wb = Workbook()
        ws = wb.active
        ws.title = "SSH Results"

        # Header
        headers = ["Hostname", "IP", "Port", "Timestamp", "Output", "Error"]
        ws.append(headers)

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        for host in hosts:
            ws.append([
                host.get("hostname", ""),
                host.get("ip", ""),
                host.get("port", ""),
                timestamp,
                host.get("output", ""),
                host.get("error", ""),
            ])

        wb.save(output_path)
        print(f"Results saved to: {output_path}")
    except Exception as e:
        print(f"Failed to save XLSX: {e}")

def load_csv(file_path):
    """Read CSV and return list of host dictionaries."""
    hosts = []
    with open(file_path, newline='') as f:
        reader = csv.DictReader(f)
        for row in reader:
            hosts.append({
                "hostname": row.get("hostname", ""),
                "ip": row.get("ip"),
                "port": row.get("port"),
            })
    return hosts

def load_json_commands(directory):
    """
    Load all JSON command files from a directory, grouped by prefix.

    Returns:
        dict: {
            "CP": {"Show Syslog": {...}},
            "POSIX": {"Disk Usage": {...}},
        }
    """
    from collections import defaultdict

    command_map = defaultdict(dict)
    for filename in os.listdir(directory):
        if filename.endswith(".json"):
            filepath = os.path.join(directory, filename)
            try:
                if os.path.getsize(filepath) == 0:
                    print(f"Skipping empty file: {filename}")
                    continue

                with open(filepath, 'r') as f:
                    command_data = json.load(f)
                    if len(command_data) != 1:
                        print(f"Skipping malformed JSON structure in: {filename}")
                        continue

                    key = list(command_data.keys())[0]
                    command_details = command_data[key]

                    # Extract category from filename prefix
                    category = filename.split('_')[0].upper()
                    command_map[category][key] = command_details

            except json.JSONDecodeError:
                print(f"Invalid JSON in file: {filename}")
            except Exception as e:
                print(f"Error loading {filename}: {e}")
    return dict(command_map)




