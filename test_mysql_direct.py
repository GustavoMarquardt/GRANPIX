import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from dotenv import load_dotenv
    load_dotenv()
    
    import mysql.connector
    
    # Usar credenciais fixas do app.py
    config = {
        'host': 'localhost',
        'user': 'root',
        'password': '',
        'database': 'granpix'
    }
    
    print("[TEST] Tentando conectar ao MySQL...")
    conn = mysql.connector.connect(**config)
    cursor = conn.cursor()
    
    print("[TEST] Conectado! Verificando tabelas...")
    
    # Ver se tabela variacoes_carros existe
    cursor.execute("SHOW TABLES LIKE 'variacoes_carros'")
    if cursor.fetchone():
        print("[OK] Tabela variacoes_carros EXISTE")
    else:
        print("[ERRO] Tabela variacoes_carros NÃO EXISTE!")
    
    # Ver se modelos_carro_loja tem dados
    cursor.execute("SELECT COUNT(*) FROM modelos_carro_loja")
    count = cursor.fetchone()[0]
    print(f"[INFO] Modelos cadastrados: {count}")
    
    # Ver se variacoes_carros tem dados
    cursor.execute("SELECT COUNT(*) FROM variacoes_carros")
    var_count = cursor.fetchone()[0]
    print(f"[INFO] Variações cadastradas: {var_count}")
    
    conn.close()
    print("[OK] Teste concluído")
    
except Exception as e:
    print(f"[ERRO] {e}")
    import traceback
    traceback.print_exc()
