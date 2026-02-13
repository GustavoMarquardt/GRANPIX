import requests
import json

try:
    print("[TEST] Testando /api/loja/carros...")
    resp = requests.get("http://localhost:5000/api/loja/carros", json={})
    
    if resp.status_code == 200:
        carros = resp.json()
        print(f"\n[SUCESSO] Carros recebidos: {len(carros)}")
        
        for carro in carros:
            print(f"\n🚗 {carro['marca'].upper()} {carro['modelo'].upper()}")
            print(f"   Preço: R$ {carro['preco']}")
            print(f"   Variações: {len(carro.get('variacoes', []))}")
            
            for i, var in enumerate(carro.get('variacoes', []), 1):
                print(f"     [{i}] Motor: {var['pecas'].get('motor', 'N/A')}")
                print(f"         Câmbio: {var['pecas'].get('cambio', 'N/A')}")
    else:
        print(f"[ERRO] Status: {resp.status_code}")
        print(f"Response: {resp.text[:500]}")
        
except Exception as e:
    print(f"[ERRO] {e}")
