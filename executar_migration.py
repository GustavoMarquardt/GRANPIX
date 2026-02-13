#!/usr/bin/env python
"""
Script para executar a migration de remoção de colunas
Este script contorna o problema de conexão do MySQL
"""
import sys
import os

# Adicionar o diretório atual ao path
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

from src.database import DatabaseManager

def main():
    print("\n" + "="*70)
    print("MIGRATION: Remover colunas redundantes da tabela CARROS")
    print("="*70 + "\n")
    
    try:
        # Inicializar DatabaseManager
        db = DatabaseManager()
        print("[MIGRATION] ✓ Conectado ao banco de dados")
        
        # Colunas a remover
        colunas = ['motor_id', 'cambio_id', 'suspensao_id', 'kit_angulo_id', 'diferencial_id']
        
        removidas = []
        erros = []
        
        for coluna in colunas:
            try:
                conn = db._get_conn()
                cursor = conn.cursor()
                
                sql = f"ALTER TABLE carros DROP COLUMN {coluna}"
                print(f"\n[MIGRATION] Executando: {sql}")
                
                cursor.execute(sql)
                conn.commit()
                
                cursor.close()
                conn.close()
                
                removidas.append(coluna)
                print(f"[MIGRATION] ✓ Coluna '{coluna}' removida com sucesso")
                
            except Exception as e:
                erro_msg = str(e)
                if 'Unknown column' in erro_msg:
                    print(f"[MIGRATION] ⚠ Coluna '{coluna}' não existe (já foi removida)")
                    removidas.append(coluna)
                else:
                    erros.append({'coluna': coluna, 'erro': erro_msg})
                    print(f"[MIGRATION] ✗ Erro ao remover '{coluna}':")
                    print(f"            {erro_msg}")
        
        print("\n" + "="*70)
        print(f"RESULTADO: {len(removidas)} coluna(s) processada(s), {len(erros)} erro(s)")
        print("="*70 + "\n")
        
        if erros:
            print("ERROS:")
            for erro in erros:
                print(f"  - {erro['coluna']}: {erro['erro']}\n")
            return 1
        else:
            print("✓ Migration concluída com sucesso!")
            return 0
            
    except Exception as e:
        print(f"\n[ERRO] Falha ao conectar ao banco de dados:")
        print(f"       {e}\n")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == '__main__':
    sys.exit(main())
