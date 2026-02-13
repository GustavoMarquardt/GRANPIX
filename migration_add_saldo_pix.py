#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Migração: Adicionar coluna saldo_pix na tabela equipes
"""

import mysql.connector

def executar_migracao():
    """Executa a migração das colunas"""
    try:
        # Conecta ao banco
        conexao = mysql.connector.connect(
            host="localhost",
            user="root",
            password="",
            database="granpix",
            charset='utf8mb4'
        )
        cursor = conexao.cursor(dictionary=True)
        
        print("[MIGRACAO] Iniciando adição de coluna saldo_pix em equipes...")
        
        # Adicionar coluna saldo_pix
        try:
            cursor.execute('''
                ALTER TABLE equipes 
                ADD COLUMN saldo_pix DOUBLE DEFAULT 0.0
            ''')
            print("✓ Coluna saldo_pix adicionada")
        except Exception as e:
            if "Duplicate column name" in str(e):
                print("✓ Coluna saldo_pix já existe")
            else:
                raise
        
        conexao.commit()
        print("\n✅ Migração concluída com sucesso!")
        
    except Exception as e:
        print(f"\n❌ Erro na migração: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if cursor:
            cursor.close()
        if conexao:
            conexao.close()

if __name__ == "__main__":
    executar_migracao()
