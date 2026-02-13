#!/usr/bin/env python3
from src.mysql_utils import get_connection

conn = get_connection()
c = conn.cursor(dictionary=True)

print("Alterando ENUM da coluna status para incluir 'finalizado'...")

# Alterar o ENUM para novos valores com 'finalizado'
c.execute("""
    ALTER TABLE volta 
    MODIFY COLUMN status ENUM('andando', 'proximo', 'aguardando', 'finalizado')
""")

conn.commit()
print("✓ ENUM atualizado para: 'andando', 'proximo', 'aguardando', 'finalizado'")

c.close()
conn.close()
