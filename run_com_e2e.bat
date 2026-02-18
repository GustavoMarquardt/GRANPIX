@echo off
REM Sobe o app com TEST_E2E=1 para rodar todos os testes E2E (incl. loja peças -> carro ativo + PIX)
set TEST_E2E=1
flask run
