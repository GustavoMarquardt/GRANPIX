#!/usr/bin/env python3
"""Entrypoint para o container: espera o banco e inicia o comando."""
import os
import sys

from wait_for_db import main as wait_main

if __name__ == "__main__":
    if wait_main() != 0:
        sys.exit(1)
    # exec do comando passado (ex.: python app.py)
    cmd = sys.argv[1:] if len(sys.argv) > 1 else ["python", "app.py"]
    os.execvp(cmd[0], cmd)
