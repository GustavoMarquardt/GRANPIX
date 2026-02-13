#!/usr/bin/env python
"""
Test script para validar cadastro de variações
"""

import requests
import json

BASE_URL = "http://localhost:5000"

headers = {
    "Authorization": "Bearer test_token",
    "X-Equipe-ID": "test-equipe-id"
}

print("="*60)
print("TESTE: Cadastro de Variações")
print("="*60)

# Step 1: Carregar carros para obter IDs de modelo e peças
print("\n[PASSO 1] Carregando carros e peças...")
resp_carros = requests.get(f"{BASE_URL}/api/loja/carros", headers=headers)
carros = resp_carros.json()

resp_pecas = requests.get(f"{BASE_URL}/api/admin/pecas")
pecas = resp_pecas.json()

if carros and isinstance(carros, list) and len(carros) > 0:
    modelo = carros[0]
    print(f"Modelo: {modelo['marca']} {modelo['modelo']}")
    print(f"Variações existentes: {len(modelo.get('variacoes', []))}")
    
    # Encontrar um motor e câmbio
    motor = None
    cambio = None
    
    for peca in pecas:
        if peca['tipo'] == 'motor' and not motor:
            motor = peca
            print(f"Motor encontrado: {motor['nome']} (ID: {motor['id'][:8]}...)")
        if peca['tipo'] == 'cambio' and not cambio:
            cambio = peca
            print(f"Câmbio encontrado: {cambio['nome']} (ID: {cambio['id'][:8]}...)")
    
    if motor and cambio:
        print(f"\n[PASSO 2] Cadastrando nova variação...")
        
        resp_var = requests.post(
            f"{BASE_URL}/api/admin/cadastrar-variacao",
            headers={"Content-Type": "application/json"},
            json={
                "modelo_carro_loja_id": modelo['id'],
                "motor_id": motor['id'],
                "cambio_id": cambio['id']
            }
        )
        
        resultado = resp_var.json()
        print(f"Status: {resp_var.status_code}")
        print(f"Resultado: {json.dumps(resultado, indent=2, ensure_ascii=False)}")
        
        if resultado.get('sucesso'):
            print("✅ Variação cadastrada com sucesso!")
            
            # Recarregar para verificar
            print(f"\n[PASSO 3] Verificando variações cadastradas...")
            resp_check = requests.get(f"{BASE_URL}/api/loja/carros", headers=headers)
            carros_check = resp_check.json()
            
            for c in carros_check:
                if c['id'] == modelo['id']:
                    print(f"Variações agora: {len(c.get('variacoes', []))}")
                    for i, v in enumerate(c.get('variacoes', []), 1):
                        print(f"  V{i}: Motor={v['pecas'].get('motor')}, Câmbio={v['pecas'].get('cambio')}")
        else:
            print(f"❌ Erro: {resultado.get('erro')}")
    else:
        print("❌ Peças não encontradas!")
else:
    print("❌ Nenhum carro disponível!")

print("\n" + "="*60)
