#!/usr/bin/env python3
"""Debug: Testar o endpoint /api/admin/etapa-hoje"""

import requests
import json

print("\n" + "="*70)
print("DEBUG: TESTANDO ENDPOINT /api/admin/etapa-hoje")
print("="*70)

try:
    resp = requests.get('http://localhost:5000/api/admin/etapa-hoje', timeout=5)
    print(f"\n✅ Status Code: {resp.status_code}")
    print(f"✅ Headers: {dict(resp.headers)}")
    
    data = resp.json()
    print(f"\n📋 Response JSON:")
    print(json.dumps(data, indent=2, default=str))
    
except Exception as e:
    print(f"\n❌ Erro ao conectar: {e}")
    print("   Flask pode não estar rodando em localhost:5000")

print("\n" + "="*70 + "\n")
