# ssh_worker.py
"""
Handles threaded SSH connection and command execution.
Each function should run in a thread and safely report back to the queue.
"""

import paramiko
import re
from config import TIMEOUT, DEBUG


def run_ssh_task(host_info, command_info, queue):
    """
    Connect to a single host, execute command, parse result, and return output.
    
    Args:
        host_info (dict): Contains 'ip', 'port', 'username', 'password', and 'hostname'.
        command_info (dict): Contains 'command' and 'parse' regex.
        queue (Queue): Shared queue to return results to the GUI.
    """
    result = {
        "hostname": host_info.get("hostname"),
        "ip": host_info.get("ip"),
        "port": host_info.get("port"),
        "output": "",
        "error": ""
    }

    # Validate required connection fields
    required_fields = ["ip", "port", "username", "password"]
    missing_fields = [field for field in required_fields if not host_info.get(field)]
    if missing_fields:
        result["error"] = f"Missing required fields: {', '.join(missing_fields)}"
        queue.put(result)
        return

    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    try:
        if DEBUG:
            print(f"[DEBUG] Connecting to {host_info['ip']}:{host_info['port']} as {host_info['username']}")

        ssh.connect(
            hostname=host_info["ip"],
            port=int(host_info["port"]),
            username=host_info["username"],
            password=host_info["password"],
            timeout=TIMEOUT
        )

        if DEBUG:
            print(f"[DEBUG] Executing command: {command_info['command']}")

        stdin, stdout, stderr = ssh.exec_command(command_info["command"])
        output = stdout.read().decode()
        result["output"] = "PARSE_ERROR"

        if DEBUG:
            print(f"[DEBUG] Raw output from {host_info['ip']}:\n{output}")

        try:
            match = re.search(command_info["parse"], output)
            if match:
                result["output"] = match.group(1)
            else:
                result["error"] = "Parse failed: pattern not found"
        except re.error as re_err:
            result["error"] = f"Regex error: {re_err}"

    except paramiko.AuthenticationException:
        result["error"] = "Authentication failed"
    except paramiko.SSHException as ssh_err:
        result["error"] = f"SSH error: {ssh_err}"
    except Exception as e:
        result["error"] = f"Unexpected error: {e}"
    finally:
        try:
            ssh.close()
        except Exception:
            if DEBUG:
                print(f"[DEBUG] Failed to close SSH connection for {host_info['ip']}")

    queue.put(result)
