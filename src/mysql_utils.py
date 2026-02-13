import mysql.connector
from mysql.connector import Error

# Altere os dados conforme seu ambiente
DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',         # Altere se não for root
    'password': '',         # Coloque sua senha
    'database': 'granpix'   # Nome do banco criado
}

def get_connection():
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        if conn.is_connected():
            return conn
    except Error as e:
        print(f"Erro ao conectar ao MySQL: {e}")
    return None

def close_connection(conn):
    if conn and conn.is_connected():
        conn.close()

# Funções auxiliares para operações comuns
def execute_query(query, params=None, fetch=False):
    """Executa uma query e opcionalmente retorna resultados"""
    conn = get_connection()
    if not conn:
        return None

    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute(query, params or ())
        if fetch:
            result = cursor.fetchall()
        else:
            conn.commit()
            result = cursor.rowcount
        return result
    except Error as e:
        print(f"Erro na query: {e}")
        return None
    finally:
        close_connection(conn)

def insert_record(table, data):
    """Insere um registro em uma tabela"""
    columns = ', '.join(data.keys())
    placeholders = ', '.join(['%s'] * len(data))
    query = f"INSERT INTO {table} ({columns}) VALUES ({placeholders})"
    return execute_query(query, list(data.values()))

def update_record(table, data, where_clause, where_params):
    """Atualiza um registro em uma tabela"""
    set_clause = ', '.join([f"{k} = %s" for k in data.keys()])
    query = f"UPDATE {table} SET {set_clause} WHERE {where_clause}"
    params = list(data.values()) + where_params
    return execute_query(query, params)

def select_records(table, where_clause=None, params=None, limit=None):
    """Seleciona registros de uma tabela"""
    query = f"SELECT * FROM {table}"
    if where_clause:
        query += f" WHERE {where_clause}"
    if limit:
        query += f" LIMIT {limit}"
    return execute_query(query, params, fetch=True)
