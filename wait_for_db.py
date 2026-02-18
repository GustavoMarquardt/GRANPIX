#!/usr/bin/env python3
"""Aguarda o host:porta do banco ficar disponível (para uso no Docker)."""
import os
import socket
import sys
import time

def main():
    host = os.environ.get("WAIT_HOST", "db")
    port = int(os.environ.get("WAIT_PORT", "3306"))
    timeout = int(os.environ.get("WAIT_TIMEOUT", "60"))
    deadline = time.monotonic() + timeout
    print(f"Aguardando {host}:{port} (timeout {timeout}s)...", flush=True)
    while time.monotonic() < deadline:
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(2)
            s.connect((host, port))
            s.close()
            print("Banco disponível.", flush=True)
            return 0
        except (socket.error, OSError):
            time.sleep(2)
    print("Timeout aguardando o banco.", flush=True)
    return 1

if __name__ == "__main__":
    sys.exit(main())
