#!/usr/bin/env python3
"""Script para aplicar a migration da tabela etapa_notas"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from app import app, api

print("\n" + "="*70)
print("🔄 APLICANDO MIGRATION: Tabela etapa_notas")
print("="*70 + "\n")

try:
    with app.app_context():
        conn = api.db._get_conn()
        cursor = conn.cursor(dictionary=True)
        
        # Verificar se a tabela já existe
        cursor.execute("SHOW TABLES LIKE 'etapa_notas'")
        existe = cursor.fetchone()
        
        if existe:
            print("✓ Tabela etapa_notas já existe")
        else:
            print("📝 Criando tabela etapa_notas...")
            
            # Criar tabela
            cursor.execute('''
                CREATE TABLE etapa_notas (
                    id VARCHAR(36) PRIMARY KEY DEFAULT (UUID()),
                    etapa_id VARCHAR(36) NOT NULL,
                    equipe_id VARCHAR(36) NOT NULL,
                    nota_linha INT DEFAULT 0 COMMENT 'Nota de linha (0-40)',
                    nota_angulo INT DEFAULT 0 COMMENT 'Nota de ângulo (0-30)',
                    nota_estilo INT DEFAULT 0 COMMENT 'Nota de estilo (0-30)',
                    data_criacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    data_atualizacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    UNIQUE KEY unique_etapa_equipe (etapa_id, equipe_id),
                    INDEX idx_etapa_id (etapa_id),
                    INDEX idx_equipe_id (equipe_id)
                )
            ''')
            
            conn.commit()
            print("✓ Tabela etapa_notas criada com sucesso!")
        
        cursor.close()
        conn.close()
        
        print("\n" + "="*70)
        print("✅ MIGRATION COMPLETA!")
        print("="*70 + "\n")
        
except Exception as e:
    print(f"\n❌ ERRO ao aplicar migration:\n{e}\n")
    import traceback
    traceback.print_exc()
    sys.exit(1)
