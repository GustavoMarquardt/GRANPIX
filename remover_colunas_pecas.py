"""
Script para remover as colunas de peças da tabela carros
As peças agora são referenciadas apenas pela tabela 'pecas' com carro_id
"""

import mysql.connector
from src.database import DatabaseManager

def remover_colunas_pecas():
    """Remove as colunas de peças individuais da tabela carros"""
    try:
        db = DatabaseManager()
        conn = db._get_conn()
        cursor = conn.cursor()
        
        colunas_para_remover = [
            'motor_id',
            'cambio_id',
            'suspensao_id',
            'kit_angulo_id',
            'diferencial_id'
        ]
        
        print("🔍 Verificando quais colunas existem na tabela carros...")
        cursor.execute("DESCRIBE carros")
        colunas_existentes = [col[0] for col in cursor.fetchall()]
        print(f"Colunas existentes: {colunas_existentes}\n")
        
        # Remover apenas as colunas que existem
        colunas_a_remover = [col for col in colunas_para_remover if col in colunas_existentes]
        
        if not colunas_a_remover:
            print("✅ Nenhuma coluna para remover - tudo já está limpo!")
            return True
        
        print(f"🗑️ Removendo {len(colunas_a_remover)} coluna(s)...")
        
        for coluna in colunas_a_remover:
            print(f"   - Removendo coluna '{coluna}'...")
            sql = f"ALTER TABLE carros DROP COLUMN {coluna}"
            cursor.execute(sql)
            print(f"     ✅ Coluna '{coluna}' removida")
        
        conn.commit()
        cursor.close()
        conn.close()
        
        print("\n✅ Todas as colunas foram removidas com sucesso!")
        print("ℹ️  As peças agora são referenciadas apenas pela tabela 'pecas' com carro_id")
        return True
        
    except Exception as e:
        print(f"\n❌ ERRO ao remover colunas: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("=" * 60)
    print("REMOVENDO COLUNAS DE PEÇAS DA TABELA CARROS")
    print("=" * 60)
    print()
    
    sucesso = remover_colunas_pecas()
    
    if sucesso:
        print("\n✅ Operação concluída com sucesso!")
    else:
        print("\n❌ Operação falhou!")
