#!/usr/bin/env python3
"""
Reseta as tabelas: solicitacoes_pecas, solicitacoes_carros e pecas.
Não mexe em pecas_loja, carros, upgrades, etc.

Rodar: python scripts/resetar_pecas_e_solicitacoes.py
"""
import os
import sys
import re

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
        v = 'mysql://root:granpix@127.0.0.1:3307/granpix'
    return v


def main():
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
        print(f'Erro de conexão: {e}')
        sys.exit(1)

    cursor = conn.cursor()
    try:
        cursor.execute('SET FOREIGN_KEY_CHECKS = 0')
        cursor.execute('DELETE FROM solicitacoes_pecas')
        n_sol_pecas = cursor.rowcount
        cursor.execute('DELETE FROM solicitacoes_carros')
        n_sol_carros = cursor.rowcount
        cursor.execute('DELETE FROM pecas')
        n_pecas = cursor.rowcount
        conn.commit()
        cursor.execute('SET FOREIGN_KEY_CHECKS = 1')
        conn.commit()
        print(f'Solicitações de peças: {n_sol_pecas} registro(s) removido(s).')
        print(f'Solicitações de carros: {n_sol_carros} registro(s) removido(s).')
        print(f'Peças: {n_pecas} registro(s) removido(s).')
        print('Peças e solicitações resetadas.')
    except Exception as e:
        conn.rollback()
        print(f'Erro: {e}')
        sys.exit(1)
    finally:
        cursor.close()
        conn.close()


if __name__ == '__main__':
    main()
