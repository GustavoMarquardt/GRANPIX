#!/usr/bin/env python3
"""Test script for serie feature in equipes"""

import requests
import json

BASE_URL = "http://localhost:5000"

def test_serie_feature():
    """Test the serie feature for team registration"""
    
    print("\n" + "="*60)
    print("TESTE DE FEATURE: SÉRIE DE EQUIPES")
    print("="*60)
    
    # Test 1: Try to create an equipe with Serie A
    print("\n[TEST 1] Criando equipe com Série A...")
    payload_a = {
        "nome": "Team Série A Test",
        "doricoins": 10000,
        "senha": "senha123",
        "serie": "A"
    }
    
    response = requests.post(
        f"{BASE_URL}/api/admin/cadastrar-equipe",
        json=payload_a,
        headers={"Content-Type": "application/json"}
    )
    
    print(f"Status: {response.status_code}")
    result_a = response.json()
    print(f"Resultado: {json.dumps(result_a, indent=2, ensure_ascii=False)}")
    
    if result_a.get('sucesso'):
        equipe_id_a = result_a.get('equipe_id')
        print(f"✅ Equipe Série A criada: {equipe_id_a}")
        
        # Get the equipe details
        get_response = requests.get(f"{BASE_URL}/api/equipes/{equipe_id_a}")
        equipe_data = get_response.json()
        print(f"Dados da equipe: {json.dumps(equipe_data, indent=2, ensure_ascii=False)}")
        
        if 'serie' in equipe_data:
            if equipe_data['serie'] == 'A':
                print(f"✅ Série armazenada corretamente: {equipe_data['serie']}")
            else:
                print(f"❌ Série incorreta: {equipe_data['serie']}")
        else:
            print("⚠️ Campo 'serie' não encontrado na resposta")
    else:
        print(f"❌ Erro ao criar equipe: {result_a.get('erro', 'Desconhecido')}")
    
    # Test 2: Create an equipe with Serie B
    print("\n[TEST 2] Criando equipe com Série B...")
    payload_b = {
        "nome": "Team Série B Test",
        "doricoins": 15000,
        "senha": "senha456",
        "serie": "B"
    }
    
    response = requests.post(
        f"{BASE_URL}/api/admin/cadastrar-equipe",
        json=payload_b,
        headers={"Content-Type": "application/json"}
    )
    
    print(f"Status: {response.status_code}")
    result_b = response.json()
    print(f"Resultado: {json.dumps(result_b, indent=2, ensure_ascii=False)}")
    
    if result_b.get('sucesso'):
        equipe_id_b = result_b.get('equipe_id')
        print(f"✅ Equipe Série B criada: {equipe_id_b}")
        
        # Get the equipe details
        get_response = requests.get(f"{BASE_URL}/api/equipes/{equipe_id_b}")
        equipe_data = get_response.json()
        
        if 'serie' in equipe_data:
            if equipe_data['serie'] == 'B':
                print(f"✅ Série armazenada corretamente: {equipe_data['serie']}")
            else:
                print(f"❌ Série incorreta: {equipe_data['serie']}")
        else:
            print("⚠️ Campo 'serie' não encontrado na resposta")
    else:
        print(f"❌ Erro ao criar equipe: {result_b.get('erro', 'Desconhecido')}")
    
    # Test 3: List all equipes and check serie field
    print("\n[TEST 3] Listando todas as equipes...")
    response = requests.get(f"{BASE_URL}/api/admin/equipes")
    print(f"Status: {response.status_code}")
    
    all_equipes = response.json()
    if isinstance(all_equipes, list):
        print(f"Total de equipes: {len(all_equipes)}")
        for eq in all_equipes[-3:]:  # Show last 3
            print(f"  - {eq.get('nome', 'N/A')}: Série = {eq.get('serie', 'N/A')}")
    
    print("\n" + "="*60)
    print("TESTES COMPLETADOS!")
    print("="*60 + "\n")

if __name__ == "__main__":
    test_serie_feature()
