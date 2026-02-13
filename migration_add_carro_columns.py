#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Migração: Adicionar colunas carro_id, carro_anterior_id e tipo_solicitacao à tabela solicitacoes_carros
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
        
        print("[MIGRACAO] Iniciando adição de colunas em solicitacoes_carros...")
        
        # 1. Adicionar coluna carro_id
        try:
            cursor.execute('''
                ALTER TABLE solicitacoes_carros 
                ADD COLUMN carro_id VARCHAR(64) AFTER equipe_id
            ''')
            print("✓ Coluna carro_id adicionada")
        except Exception as e:
            if "Duplicate column name" in str(e):
                print("✓ Coluna carro_id já existe")
            else:
                raise
        
        # 2. Adicionar coluna carro_anterior_id
        try:
            cursor.execute('''
                ALTER TABLE solicitacoes_carros 
                ADD COLUMN carro_anterior_id VARCHAR(64) AFTER carro_id
            ''')
            print("✓ Coluna carro_anterior_id adicionada")
        except Exception as e:
            if "Duplicate column name" in str(e):
                print("✓ Coluna carro_anterior_id já existe")
            else:
                raise
        
        # 3. Adicionar coluna tipo_solicitacao
        try:
            cursor.execute('''
                ALTER TABLE solicitacoes_carros 
                ADD COLUMN tipo_solicitacao VARCHAR(64) DEFAULT 'ativacao' AFTER tipo_carro
            ''')
            print("✓ Coluna tipo_solicitacao adicionada")
        except Exception as e:
            if "Duplicate column name" in str(e):
                print("✓ Coluna tipo_solicitacao já existe")
            else:
                raise
        
        # 4. Adicionar Foreign Keys
        try:
            cursor.execute('''
                ALTER TABLE solicitacoes_carros 
                ADD CONSTRAINT fk_carro_id 
                FOREIGN KEY (carro_id) REFERENCES carros(id)
            ''')
            print("✓ Foreign Key carro_id adicionada")
        except Exception as e:
            if "Duplicate key name" in str(e) or "Duplicate constraint name" in str(e):
                print("✓ Foreign Key carro_id já existe")
            else:
                raise
        
        try:
            cursor.execute('''
                ALTER TABLE solicitacoes_carros 
                ADD CONSTRAINT fk_carro_anterior_id 
                FOREIGN KEY (carro_anterior_id) REFERENCES carros(id)
            ''')
            print("✓ Foreign Key carro_anterior_id adicionada")
        except Exception as e:
            if "Duplicate key name" in str(e) or "Duplicate constraint name" in str(e):
                print("✓ Foreign Key carro_anterior_id já existe")
            else:
                raise
        
        # 5. Adicionar índices
        try:
            cursor.execute('''
                ALTER TABLE solicitacoes_carros 
                ADD INDEX idx_carro_id (carro_id)
            ''')
            print("✓ Índice carro_id adicionado")
        except Exception as e:
            if "Duplicate key name" in str(e):
                print("✓ Índice carro_id já existe")
            else:
                raise
        
        try:
            cursor.execute('''
                ALTER TABLE solicitacoes_carros 
                ADD INDEX idx_tipo_solicitacao (tipo_solicitacao)
            ''')
            print("✓ Índice tipo_solicitacao adicionado")
        except Exception as e:
            if "Duplicate key name" in str(e):
                print("✓ Índice tipo_solicitacao já existe")
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
