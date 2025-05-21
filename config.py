# config.py
"""
Global configuration for the SSH Host Logger tool.
Defines threading, logging, file structure, and input validation.
"""

MAX_THREADS = 5
TIMEOUT = 10  # seconds
DEBUG = True

LOG_PATH = "logs/error.log"
COMMANDS_DIR = "config"
HOST_CSV = "assets/hosts.csv"

# Required CSV columns (case-sensitive)
CSV_REQUIRED_COLUMNS = ["hostname", "ip", "port"]
