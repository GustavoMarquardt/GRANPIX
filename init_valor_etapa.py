#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Script para inicializar o valor padrão de etapa nas configurações
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.database import Database

def main():
    db = Database()
    
    # Verificar se já existe valor_etapa
    conn = db._get_conn()
    cursor = conn.cursor()
    cursor.execute('SELECT valor FROM configuracoes WHERE chave = %s', ('valor_etapa',))
    resultado = cursor.fetchone()
    
    if resultado:
        print(f"✓ valor_etapa já existe: R$ {resultado['valor']}")
    else:
        print("Inserindo valor_etapa padrão de R$ 1000.00...")
        sucesso = db.salvar_configuracao('valor_etapa', '1000.00', 'Valor padrão cobrado para participar de uma etapa')
        
        if sucesso:
            print("✓ valor_etapa criado com sucesso!")
        else:
            print("✗ Erro ao criar valor_etapa")
    
    conn.close()

if __name__ == '__main__':
    main()
