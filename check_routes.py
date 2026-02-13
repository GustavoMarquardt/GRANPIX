#!/usr/bin/env python
# -*- coding: utf-8 -*-
import sys
import os

# Adicionar o diretório ao path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    import app as app_module
    
    print("\n=== PROCURANDO POR ROTAS COM 'instalar' e 'multiplas' ===\n")
    
    found = False
    for rule in app_module.app.url_map.iter_rules():
        rule_str = str(rule)
        if 'instalar' in rule_str.lower() and 'multiplas' in rule_str.lower():
            print(f"✅ ENCONTRADA: {rule}")
            found = True
    
    if not found:
        print("❌ NENHUMA ROTA ENCONTRADA COM 'instalar' E 'multiplas'")
        print("\n=== TODAS AS ROTAS /api/garagem ===\n")
        for rule in app_module.app.url_map.iter_rules():
            rule_str = str(rule)
            if '/api/garagem' in rule_str:
                print(f"  {rule}")
    
except Exception as e:
    print(f"ERRO: {e}")
    import traceback
    traceback.print_exc()
