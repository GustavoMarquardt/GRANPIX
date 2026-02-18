"""
Configuração dos testes E2E com Playwright.
O app deve estar rodando (ex.: http://localhost:5000) antes de rodar estes testes.
"""
import os
import pytest


@pytest.fixture(scope="session")
def base_url():
    """URL base do app. Use BASE_URL para outro host/porta."""
    return os.environ.get("BASE_URL", "http://localhost:5000")
