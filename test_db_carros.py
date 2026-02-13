import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from src.database import DatabaseManager
    
    db = DatabaseManager()
    print("[TEST] Conectando ao banco...")
    
    # Contar carros
    import mysql.connector
    conn = db._get_conn()
    cursor = conn.cursor()
    
    cursor.execute('SELECT COUNT(*) FROM modelos_carro_loja')
    count = cursor.fetchone()[0]
    print(f"[TEST] Total de carros no banco: {count}")
    
    if count > 0:
        cursor.execute('SELECT id, marca, modelo FROM modelos_carro_loja LIMIT 5')
        print(f"[TEST] Primeiros carros:")
        for row in cursor.fetchall():
            print(f"  - {row[1]} {row[2]}")
    
    # Contar variações
    cursor.execute('SELECT COUNT(*) FROM variacoes_carros')
    var_count = cursor.fetchone()[0]
    print(f"[TEST] Total de variações: {var_count}")
    
    conn.close()
    
except Exception as e:
    print(f"[ERRO] {e}")
    import traceback
    traceback.print_exc()
