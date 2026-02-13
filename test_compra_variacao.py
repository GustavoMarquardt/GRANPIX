#!/usr/bin/env python
"""
Test script to verify purchase flow works with variations
"""

import requests
import json

BASE_URL = "http://localhost:5000"

# First, create a team to test purchase
headers = {
    "Authorization": "Bearer test_token",
    "X-Equipe-ID": "test-team-123"
}

print("="*60)
print("TESTE: Fluxo de Compra com Variações")
print("="*60)

# Step 1: Get cars with variations
print("\n[PASSO 1] Obtendo carros com variações...")
resp = requests.get(f"{BASE_URL}/api/loja/carros", headers=headers)
data = resp.json()

if isinstance(data, list) and len(data) > 0:
    carro = data[0]
    print(f"Carro: {carro['marca']} {carro['modelo']}")
    
    if carro.get('variacoes') and len(carro['variacoes']) > 0:
        variacao = carro['variacoes'][0]
        variacao_id = variacao.get('id')
        print(f"Primeira Variação ID: {variacao_id}")
        print(f"Peças: Motor={variacao.get('pecas', {}).get('motor')}, Câmbio={variacao.get('pecas', {}).get('cambio')}")
        
        # Step 2: Try to purchase car with variation
        print(f"\n[PASSO 2] Tentando comprar carro com variação {variacao_id[:8]}...")
        
        purchase_body = {
            "tipo": "carro",
            "variacao_id": variacao_id
        }
        
        resp_purchase = requests.post(
            f"{BASE_URL}/api/comprar",
            headers=headers,
            json=purchase_body
        )
        
        purchase_result = resp_purchase.json()
        print(f"Status: {resp_purchase.status_code}")
        print(f"Resposta: {json.dumps(purchase_result, indent=2, ensure_ascii=False)}")
        
        if purchase_result.get('sucesso'):
            print("✅ Compra com variação funcionou!")
        else:
            print(f"❌ Erro na compra: {purchase_result.get('erro', 'Unknown error')}")
    else:
        print("❌ Carro sem variações!")
else:
    print("❌ Nenhum carro disponível!")

print("\n" + "="*60)
print("Teste completado!")
