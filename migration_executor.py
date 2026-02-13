#!/usr/bin/env python3
"""
Script para executar migration através do endpoint Flask
"""
import sys
import os
import json

# Adicionar path
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

def main():
    print("\n" + "="*70)
    print("MIGRATION via Flask: Remover colunas da tabela CARROS")
    print("="*70 + "\n")
    
    try:
        # Importar a aplicação Flask
        from app import app, api
        
        # Criar contexto de aplicação
        with app.app_context():
            print("[MIGRATION] ✓ Conectado à aplicação Flask")
            
            # Simular sessão de admin
            from flask import session
            session['admin'] = True
            
            # Colunas a remover
            colunas = ['motor_id', 'cambio_id', 'suspensao_id', 'kit_angulo_id', 'diferencial_id']
            
            removidas = []
            erros = []
            
            print("[MIGRATION] Iniciando remoção de colunas...\n")
            
            for coluna in colunas:
                try:
                    conn = api.db._get_conn()
                    cursor = conn.cursor()
                    
                    sql = f"ALTER TABLE carros DROP COLUMN IF EXISTS {coluna}"
                    print(f"[MIGRATION] Executando: {sql}")
                    
                    cursor.execute(sql)
                    conn.commit()
                    
                    cursor.close()
                    conn.close()
                    
                    removidas.append(coluna)
                    print(f"[MIGRATION] ✓ Coluna '{coluna}' removida com sucesso\n")
                    
                except Exception as e:
                    erro_msg = str(e)
                    if 'Unknown column' in erro_msg or 'check that column/key exists' in erro_msg.lower():
                        print(f"[MIGRATION] ⚠ Coluna '{coluna}' não existe (já foi removida)\n")
                        removidas.append(coluna)
                    else:
                        erros.append({'coluna': coluna, 'erro': erro_msg})
                        print(f"[MIGRATION] ✗ Erro: {erro_msg}\n")
            
            print("="*70)
            print(f"RESULTADO: {len(removidas)} coluna(s) processada(s), {len(erros)} erro(s)")
            print("="*70 + "\n")
            
            if removidas:
                print(f"✓ Colunas removidas: {', '.join(removidas)}")
            
            if erros:
                print(f"\n✗ Erros encontrados:")
                for erro in erros:
                    print(f"  - {erro['coluna']}: {erro['erro']}")
                return 1
            else:
                print("\n✓ Migration concluída com sucesso!")
                return 0
            
    except ImportError as e:
        print(f"[ERRO] Falha ao importar aplicação:")
        print(f"       {e}\n")
        return 1
    except Exception as e:
        print(f"[ERRO] Erro durante migration:")
        print(f"       {e}\n")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == '__main__':
    sys.exit(main())
