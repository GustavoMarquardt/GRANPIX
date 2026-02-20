@echo off
REM Roda o teste E2E visual da etapa completa (qualify + notas + batalhas).
REM IMPORTANTE: O app deve estar rodando com TEST_E2E=1 (ex.: execute run_com_e2e.bat em outro terminal).
echo.
echo Execute primeiro em outro terminal: run_com_e2e.bat
echo Depois rode este script para ver o teste na tela.
echo.
pytest tests/e2e/test_etapa_completa_visual.py -v -s --headed
