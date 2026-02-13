import mysql.connector

try:
    print("[TEST] Conectando ao MySQL (localhost, user=root, password='')...")
    conn = mysql.connector.connect(
        host='localhost',
        user='root',
        password='',
        database='granpix'
    )
    cursor = conn.cursor()
    
    print("[TEST] Conectado com sucesso!")
    
    # Ver tabelas
    cursor.execute("SHOW TABLES")
    print("\n[INFO] Tabelas no banco:")
    for (table,) in cursor.fetchall():
        print(f"  - {table}")
    
    # Verificar especificamente
    print("\n[INFO] Verificando tabelas críticas:")
    cursor.execute("SHOW TABLES LIKE 'modelos_carro_loja'")
    if cursor.fetchone():
        print("  ✓ modelos_carro_loja EXISTS")
    else:
        print("  ✗ modelos_carro_loja NOT FOUND")
        
    cursor.execute("SHOW TABLES LIKE 'variacoes_carros'")
    if cursor.fetchone():
        print("  ✓ variacoes_carros EXISTS")
    else:
        print("  ✗ variacoes_carros NOT FOUND")
    
    # Contar dados
    print("\n[INFO] Dados no banco:")
    cursor.execute("SELECT COUNT(*) FROM modelos_carro_loja")
    print(f"  Carros: {cursor.fetchone()[0]}")
    
    cursor.execute("SELECT COUNT(*) FROM variacoes_carros")
    print(f"  Variações: {cursor.fetchone()[0]}")
    
    conn.close()
    
except Exception as e:
    print(f"[ERRO] {e}")
