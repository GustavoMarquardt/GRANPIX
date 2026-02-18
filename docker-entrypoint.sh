#!/bin/sh
set -e

# Esperar o MariaDB estar aceitando conexões (usado pelo docker-compose)
python wait_for_db.py || exit 1

echo "Iniciando aplicação..."
exec "$@"
