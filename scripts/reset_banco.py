#!/usr/bin/env python3
"""
Reseta todo o banco de dados (zera todas as tabelas).
Requer: MYSQL_CONFIG no .env ou variável de ambiente.

Rodar: python scripts/reset_banco.py

ATENÇÃO: Este script apaga TODOS os dados. Use com cuidado!
"""
import os
import sys

_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _root)
os.chdir(_root)

try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(_root, '.env'))
except ImportError:
    pass


def _load_mysql_config():
    v = os.environ.get('MYSQL_CONFIG', '').strip()
    if not v and os.path.exists(os.path.join(_root, '.env')):
        with open(os.path.join(_root, '.env'), encoding='utf-8') as f:
            for line in f:
                if line.strip().startswith('MYSQL_CONFIG='):
                    v = line.split('=', 1)[1].strip().strip('"\'')
                    break
    if not v:
        # Fallback: Docker mapeia MariaDB na porta 3307; sem senha para root local
        v = 'mysql://root:granpix@127.0.0.1:3307/granpix'
    return v


def main():
    import re
    import pymysql

    config = _load_mysql_config()
    m = re.match(r"mysql://([^:@]+)(?::([^@]*))?@([^:/]+)(?::(\d+))?/([^?]+)", config)
    if not m:
        print('Erro: string de conexão MySQL inválida.')
        sys.exit(1)
    user, password, host, port, db = m.groups()
    password = password or ''
    port = int(port) if port else 3306

    print(f'Conectando a {host}:{port}/{db}...')
    try:
        conn = pymysql.connect(
            host=host,
            user=user,
            password=password,
            port=port,
            database=db,
            charset='utf8mb4',
        )
    except pymysql.err.OperationalError as e:
        if e.args[0] == 2003:
            print('Erro: não foi possível conectar ao MySQL/MariaDB.')
            print('  Verifique se o servidor está rodando (ex.: docker compose up -d db).')
        else:
            print(f'Erro de conexão: {e}')
        sys.exit(1)

    cursor = conn.cursor()

    # Obter todas as tabelas do banco (exceto views)
    cursor.execute("""
        SELECT TABLE_NAME FROM information_schema.TABLES
        WHERE TABLE_SCHEMA = %s AND TABLE_TYPE = 'BASE TABLE'
    """, (db,))
    tables = [row[0] for row in cursor.fetchall()]

    if not tables:
        print('Nenhuma tabela encontrada no banco.')
        conn.close()
        return

    print(f'Zerando {len(tables)} tabela(s)...')
    cursor.execute('SET FOREIGN_KEY_CHECKS = 0')
    for t in tables:
        if not re.match(r'^[a-zA-Z0-9_]+$', t):
            print(f'  Ignorando nome inválido: {t}')
            continue
        try:
            cursor.execute(f'TRUNCATE TABLE `{t}`')
            print(f'  OK: {t}')
        except Exception as e:
            print(f'  ERRO em {t}: {e}')

    cursor.execute('SET FOREIGN_KEY_CHECKS = 1')
    conn.commit()
    cursor.close()
    conn.close()

    print('Banco zerado com sucesso.')


if __name__ == '__main__':
    main()
