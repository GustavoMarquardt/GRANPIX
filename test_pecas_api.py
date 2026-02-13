#!/usr/bin/env python3
import sys
sys.path.insert(0, '.')
from src.api import APIGranpix

api = APIGranpix('mysql://root:@localhost:3306/granpix')

# Carregar modelos
modelos = api.db.carregar_modelos_loja()
print('MODELOS CARREGADOS:')
for modelo in modelos[:5]:
    print(f'\n{modelo.marca} {modelo.modelo}')
    if modelo.motor_id:
        motor = api.db.buscar_peca_loja_por_id(modelo.motor_id)
        print(f'  Motor: {motor.nome if motor else "Nao encontrado"}')
    if modelo.cambio_id:
        cambio = api.db.buscar_peca_loja_por_id(modelo.cambio_id)
        print(f'  Cambio: {cambio.nome if cambio else "Nao encontrado"}')
    if modelo.suspensao_id:
        suspensao = api.db.buscar_peca_loja_por_id(modelo.suspensao_id)
        print(f'  Suspensao: {suspensao.nome if suspensao else "Nao encontrado"}')
    if modelo.kit_angulo_id:
        kit = api.db.buscar_peca_loja_por_id(modelo.kit_angulo_id)
        print(f'  Kit Angulo: {kit.nome if kit else "Nao encontrado"}')
