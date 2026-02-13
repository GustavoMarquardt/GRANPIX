import requests
import json

BASE_URL = "http://localhost:5000"

try:
    print("[TEST] Tentando conectar ao app...")
    
    # Testar endpoint de carros
    resp = requests.get(f"{BASE_URL}/api/admin/carros", timeout=5)
    print(f"[TEST] GET /api/admin/carros - Status: {resp.status_code}")
    
    if resp.status_code == 200:
        carros = resp.json()
        print(f"[INFO] Carros retornados: {len(carros)}")
        if carros:
            print(f"[INFO] Primeiro carro: {carros[0].get('marca')} {carros[0].get('modelo')}")
    else:
        print(f"[ERRO] Resposta: {resp.text[:200]}")
    
except Exception as e:
    print(f"[ERRO] {e}")
    print("[INFO] O app não está rodando em http://localhost:5000")
