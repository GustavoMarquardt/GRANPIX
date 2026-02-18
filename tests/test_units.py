"""Testes unitários que não dependem do app nem do banco."""
import re


def test_mysql_url_regex():
    """Valida que o regex de conexão MySQL aceita URLs esperadas."""
    pattern = re.compile(
        r"mysql://([^:@]+)(?::([^@]*))?@([^:/]+)(?::(\d+))?/([^?]+)"
    )
    # user:pass@host:port/db
    m = pattern.match("mysql://root:granpix@db:3306/granpix")
    assert m is not None
    user, password, host, port, db = m.groups()
    assert user == "root"
    assert password == "granpix"
    assert host == "db"
    assert port == "3306"
    assert db == "granpix"

    # sem senha
    m2 = pattern.match("mysql://root:@127.0.0.1:3307/granpix_test")
    assert m2 is not None
    user2, password2, host2, port2, db2 = m2.groups()
    assert user2 == "root"
    assert password2 == ""
    assert host2 == "127.0.0.1"
    assert port2 == "3307"
    assert db2 == "granpix_test"

    # inválido
    assert pattern.match("http://example.com") is None
    assert pattern.match("mysql://nohost/") is None
