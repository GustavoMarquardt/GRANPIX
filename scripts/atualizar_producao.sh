#!/bin/bash
# Atualiza o código de produção (branch lord) no servidor.
# Uso: execute na pasta do projeto no servidor (onde o app roda atrás do Cloudflare).

set -e
BRANCH="${1:-lord}"

echo "=== Atualizando GRANPIX (branch: $BRANCH) ==="
git fetch origin
git checkout "$BRANCH"
git pull origin "$BRANCH"
echo "=== Código atualizado. ==="
echo ""
echo "Agora reinicie o app, por exemplo:"
echo "  sudo systemctl restart granpix"
echo "  # ou: sudo supervisorctl restart granpix"
echo ""
echo "Opcional: no Dashboard do Cloudflare, purge o cache (Caching -> Purge Everything) para servir a versão nova."
