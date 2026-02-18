"""Testes do módulo database (conexão e parsing)."""
import re
import pytest


class TestDatabaseManagerParsing:
    """Testes de parsing (não precisam de banco)."""

    def test_connection_string_parsing(self):
        """Parse da URL de conexão (mesmo regex do _get_conn)."""
        db_path = "mysql://user:pass@host:1234/dbname"
        m = re.match(r"mysql://([^:@]+)(?::([^@]*))?@([^:/]+)(?::(\d+))?/([^?]+)", db_path)
        assert m is not None
        assert m.group(1) == "user"
        assert m.group(2) == "pass"
        assert m.group(3) == "host"
        assert m.group(4) == "1234"
        assert m.group(5) == "dbname"


class TestDatabaseManagerConnection:
    """Testes que usam DatabaseManager (exigem app/banco; client fixture faz skip se indisponível)."""

    def test_invalid_connection_string_raises(self, client):
        """URL inválida deve levantar ValueError ao criar conexão."""
        from src.database import DatabaseManager
        with pytest.raises(ValueError, match="inválida"):
            DatabaseManager("invalid://x/y")
