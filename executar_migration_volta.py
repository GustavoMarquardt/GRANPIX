#!/usr/bin/env python3
"""
Script para executar migração da tabela volta
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import mysql.connector
from mysql.connector import Error

DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': '',
    'database': 'granpix'
}

def executar_migracao():
    """Executa a migração da tabela volta"""
    conn = None
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        print("[MIGRACAO] Conectado ao banco de dados granpix")
        
        # SQL para criar a tabela (ajustado para utf8mb4_general_ci como em outras tabelas)
        sql = """
        CREATE TABLE IF NOT EXISTS volta (
            id VARCHAR(64) PRIMARY KEY DEFAULT (UUID()),
            id_piloto VARCHAR(64) NOT NULL COLLATE utf8mb4_general_ci,
            id_equipe VARCHAR(64) NOT NULL COLLATE utf8mb4_general_ci,
            id_etapa VARCHAR(64) NOT NULL COLLATE utf8mb4_general_ci,
            nota_linha INT DEFAULT NULL CHECK (nota_linha >= 0 AND nota_linha <= 40),
            nota_angulo INT DEFAULT NULL CHECK (nota_angulo >= 0 AND nota_angulo <= 30),
            nota_estilo INT DEFAULT NULL CHECK (nota_estilo >= 0 AND nota_estilo <= 30),
            status ENUM('agendada', 'em_andamento', 'finalizada') DEFAULT 'agendada',
            data_criacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            data_atualizacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            
            UNIQUE KEY unique_volta (id_piloto, id_equipe, id_etapa),
            FOREIGN KEY (id_piloto) REFERENCES pilotos(id) ON DELETE CASCADE,
            FOREIGN KEY (id_equipe) REFERENCES equipes(id) ON DELETE CASCADE,
            FOREIGN KEY (id_etapa) REFERENCES etapas(id) ON DELETE CASCADE,
            
            INDEX idx_etapa (id_etapa),
            INDEX idx_equipe (id_equipe),
            INDEX idx_piloto (id_piloto),
            INDEX idx_status (status)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci
        """
        
        print("[MIGRACAO] Executando CREATE TABLE volta...")
        cursor.execute(sql)
        conn.commit()
        
        # Verificar se tabela foi criada
        cursor.execute("SHOW TABLES LIKE 'volta'")
        result = cursor.fetchone()
        
        if result:
            print("✓ Tabela volta criada com sucesso!")
            cursor.execute("DESC volta")
            schema = cursor.fetchall()
            print("\n[SCHEMA] Colunas da tabela:")
            for row in schema:
                print(f"  - {row[0]}: {row[1]}")
            cursor.close()
            return True
        else:
            print("✗ Tabela volta não foi criada (razão desconhecida)")
            cursor.close()
            return False
        
    except Error as e:
        print(f"✗ Erro MySQL: {e}")
        return False
    except Exception as e:
        print(f"✗ Erro geral: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        if conn and conn.is_connected():
            conn.close()
            print("[MIGRACAO] Conexão fechada")

if __name__ == '__main__':
    sucesso = executar_migracao()
    sys.exit(0 if sucesso else 1)
