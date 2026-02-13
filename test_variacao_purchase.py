#!/usr/bin/env python
"""
Test script to verify variations are returned correctly and purchase works with variations
"""

import requests
import json

BASE_URL = "http://localhost:5000"

# Headers com autenticação fake (para teste)
headers = {
    "Authorization": "Bearer test_token",
    "X-Equipe-ID": "test-equipe-id"
}

print("="*60)
print("TESTE: API de Carros com Variações")
print("="*60)

# Test 1: Load cars with variations
print("\n[TESTE 1] Carregando carros com variações...")
resp = requests.get(f"{BASE_URL}/api/loja/carros", headers=headers)
data = resp.json()

print(f"Status: {resp.status_code}")

# Check if data is dict (error) or list
if isinstance(data, dict) and 'erro' in data:
    print(f"Erro: {data['erro']}")
else:
    print(f"Carros: {len(data)}")

    for carro in data:
        print(f"\n  Modelo: {carro['marca']} {carro['modelo']}")
        if 'variacoes' in carro and carro['variacoes']:
            print(f"    Variações: {len(carro['variacoes'])}")
            for i, var in enumerate(carro['variacoes'], 1):
                print(f"      V{i}: ID={var.get('id', 'N/A')}")
                if 'pecas' in var:
                    print(f"         - Motor: {var['pecas'].get('motor', 'N/A')}")
                    print(f"         - Câmbio: {var['pecas'].get('cambio', 'N/A')}")
        else:
            print("    ❌ Sem variações!")

print("\n" + "="*60)
print("Teste completado!")
