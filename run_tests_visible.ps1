# Rodar testes E2E com navegador visível e resultado de persistência na tela.
# Requer: app rodando (ex.: flask run ou docker compose up -d) e playwright install.
#
# Uso: .\run_tests_visible.ps1

Write-Host "=== Testes E2E (navegador vai abrir - acompanhe na tela) ===" -ForegroundColor Cyan
Write-Host "App deve estar rodando em http://localhost:5000" -ForegroundColor Yellow
Write-Host ""

python -m pytest tests/e2e/ -v -s --headed

Write-Host ""
Write-Host "=== Para ver também os testes de persistência da API (carro/peça/equipe no banco) ===" -ForegroundColor Cyan
Write-Host "Rode: python -m pytest tests/test_admin.py -v -s -k persiste" -ForegroundColor Yellow
