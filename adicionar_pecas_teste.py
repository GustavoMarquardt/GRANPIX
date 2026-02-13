#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Adiciona peças de teste ao armazém via API"""

import requests
import json

# Dados
BASE_URL = 'http://localhost:5000'
equipe_id = 'c1958e11-4361-4d2c-a1c7-6ee2fc571fa8'

# Buscar peças disponíveis
print("Buscando peças disponíveis na loja...")
resp = requests.get(f'{BASE_URL}/api/loja/pecas')
pecas = resp.json()
print(f"✅ Encontradas {len(pecas)} peças")

# Exibir primeiro 3
print("\nPeças disponíveis:")
for peca in pecas[:3]:
    print(f"  - {peca['nome']} ({peca['tipo']}): {peca.get('valor', '?')} coins")
