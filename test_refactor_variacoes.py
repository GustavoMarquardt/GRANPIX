#!/usr/bin/env python3
"""Script para testar o refactor de variações de carros"""

import sys
sys.path.insert(0, '/Users/Gustavo Marquardt/Documents/GRANPIX')

from src.database import DatabaseManager
from src.loja_carros import ModeloCarro, VariacaoCarro

# Conectar ao banco
db = DatabaseManager()

print("\n" + "="*70)
print("TESTE: Carregando modelos com variações")
print("="*70)

modelos = db.carregar_modelos_loja()

print(f"\n✓ Carregados {len(modelos)} modelos")

for modelo in modelos[:3]:  # Mostrar apenas os primeiros 3
    print(f"\n  Modelo: {modelo.marca} {modelo.modelo}")
    print(f"  ID: {modelo.id}")
    print(f"  Classe: {modelo.classe}")
    print(f"  Preço: R$ {modelo.preco}")
    print(f"  Variações: {len(modelo.variacoes)}")
    
    for i, var in enumerate(modelo.variacoes, 1):
        print(f"    [{i}] Var ID: {var.id}")
        print(f"        Motor: {var.motor_id or 'Padrão'}")
        print(f"        Câmbio: {var.cambio_id or 'Padrão'}")
        print(f"        Suspensão: {var.suspensao_id or 'Padrão'}")

print("\n" + "="*70)
print("TESTE: Adicionar novo modelo com variação")
print("="*70)

novo_modelo = ModeloCarro(
    id='test-modelo-1',
    marca='Tesla',
    modelo='Model 3',
    classe='premium',
    preco=100000.0,
    descricao='Carro elétrico de luxo',
    variacoes=[
        VariacaoCarro(
            id='test-var-1',
            modelo_carro_loja_id='test-modelo-1',
            motor_id=None,
            cambio_id=None
        ),
        VariacaoCarro(
            id='test-var-2',
            modelo_carro_loja_id='test-modelo-1',
            motor_id=None,
            cambio_id=None
        )
    ]
)

salvo = db.salvar_modelo_loja(novo_modelo)
print(f"\n✓ Modelo salvo: {salvo}")

# Recarregar e verificar
modelos_novos = db.carregar_modelos_loja()
modelo_teste = next((m for m in modelos_novos if m.id == 'test-modelo-1'), None)

if modelo_teste:
    print(f"\n✓ Modelo recarregado: {modelo_teste.marca} {modelo_teste.modelo}")
    print(f"  Variações: {len(modelo_teste.variacoes)}")
else:
    print("\n✗ Modelo não encontrado após salvar")

print("\n" + "="*70)
print("TESTE CONCLUÍDO")
print("="*70 + "\n")
