#!/usr/bin/env python3
"""
Script de teste para verificar o sistema de compras:
- Criar equipe
- Login
- Comprar carros
- Comprar peças
- Verificar se as peças estão corretamente associadas
"""

import requests
import json
import time
import sys
import os

# Adicionar o diretório src ao path para importar módulos
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

BASE_URL = 'http://localhost:5000'

def criar_equipe_teste():
    """Cria uma equipe de teste via endpoint admin"""
    print("🔧 Criando equipe de teste...")

    # Dados da equipe
    equipe_data = {
        'nome': 'EquipeTesteCompra',
        'senha': 'teste123',
        'serie': 'A',
        'doricoins': 50000  # Dar mais doricoins para os testes
    }

    try:
        response = requests.post(f'{BASE_URL}/api/admin/cadastrar-equipe', json=equipe_data)
        print(f"Status: {response.status_code}")

        if response.status_code == 200:
            result = response.json()
            equipe_id = result.get('equipe', {}).get('id')
            print(f"✅ Equipe criada: {result}")
            return equipe_id, equipe_data['senha']
        else:
            print(f"❌ Erro ao criar equipe: {response.text}")
            return None, None
    except Exception as e:
        print(f"❌ Erro de conexão: {e}")
        return None, None

def fazer_login(equipe_id, senha):
    """Faz login e retorna o equipe_id confirmado"""
    print("🔑 Fazendo login...")

    login_data = {
        'tipo': 'equipe',
        'equipe_id': equipe_id,
        'senha': senha
    }

    try:
        response = requests.post(f'{BASE_URL}/login', json=login_data)
        print(f"Status: {response.status_code}")

        if response.status_code == 200:
            result = response.json()
            if result.get('sucesso'):
                equipe_id_confirmado = result.get('uuid')
                print(f"✅ Login realizado. Equipe ID confirmado: {equipe_id_confirmado}")
                return equipe_id_confirmado
            else:
                print(f"❌ Login falhou: {result}")
                return None
        else:
            print(f"❌ Erro no login: {response.text}")
            return None
    except Exception as e:
        print(f"❌ Erro de conexão: {e}")
        return None

def obter_carros_loja(equipe_id):
    """Obtém lista de carros disponíveis na loja"""
    print("🏎️ Obtendo carros da loja...")

    headers = {'X-Equipe-ID': equipe_id}

    try:
        response = requests.get(f'{BASE_URL}/api/loja/carros', headers=headers)
        print(f"Status: {response.status_code}")

        if response.status_code == 200:
            carros = response.json()
            print(f"✅ Encontrados {len(carros)} carros na loja")
            return carros
        else:
            print(f"❌ Erro ao obter carros: {response.text}")
            return []
    except Exception as e:
        print(f"❌ Erro de conexão: {e}")
        return []

def comprar_carro(equipe_id, carro_id, variacao_id=None):
    """Compra um carro"""
    print(f"💰 Comprando carro ID: {carro_id}, Variação: {variacao_id}")

    headers = {
        'Content-Type': 'application/json',
        'X-Equipe-ID': equipe_id
    }

    compra_data = {
        'tipo': 'carro',
        'item_id': carro_id
    }

    if variacao_id:
        compra_data['variacao_id'] = variacao_id

    try:
        response = requests.post(f'{BASE_URL}/api/comprar', json=compra_data, headers=headers)
        print(f"Status: {response.status_code}")

        if response.status_code == 200:
            result = response.json()
            print(f"✅ Carro comprado: {result}")
            return True
        else:
            print(f"❌ Erro ao comprar carro: {response.text}")
            return False
    except Exception as e:
        print(f"❌ Erro de conexão: {e}")
        return False

def obter_pecas_loja(equipe_id):
    """Obtém lista de peças disponíveis na loja"""
    print("🔧 Obtendo peças da loja...")

    headers = {'X-Equipe-ID': equipe_id}

    try:
        response = requests.get(f'{BASE_URL}/api/loja/pecas', headers=headers)
        print(f"Status: {response.status_code}")

        if response.status_code == 200:
            pecas = response.json()
            print(f"✅ Encontradas {len(pecas)} peças na loja")
            return pecas
        else:
            print(f"❌ Erro ao obter peças: {response.text}")
            return []
    except Exception as e:
        print(f"❌ Erro de conexão: {e}")
        return []

def comprar_peca(equipe_id, peca_id, carro_id=None):
    """Compra uma peça"""
    print(f"💰 Comprando peça ID: {peca_id}, Carro: {carro_id}")

    headers = {
        'Content-Type': 'application/json',
        'X-Equipe-ID': equipe_id
    }

    compra_data = {
        'tipo': 'peca',
        'item_id': peca_id
    }

    if carro_id:
        compra_data['carro_id'] = carro_id

    try:
        response = requests.post(f'{BASE_URL}/api/comprar', json=compra_data, headers=headers)
        print(f"Status: {response.status_code}")

        if response.status_code == 200:
            result = response.json()
            print(f"✅ Peça comprada: {result}")
            return True
        else:
            print(f"❌ Erro ao comprar peça: {response.text}")
            return False
    except Exception as e:
        print(f"❌ Erro de conexão: {e}")
        return False

def verificar_garagem(equipe_id):
    """Verifica o conteúdo da garagem"""
    print("🏁 Verificando garagem...")

    headers = {'X-Equipe-ID': equipe_id}

    try:
        response = requests.get(f'{BASE_URL}/api/garagem/{equipe_id}', headers=headers)
        print(f"Status: {response.status_code}")

        if response.status_code == 200:
            garagem = response.json()
            print("✅ Garagem obtida:")
            print(f"   Carros: {len(garagem.get('carros', []))}")
            for i, carro in enumerate(garagem.get('carros', [])):
                print(f"     Carro {i+1}: {carro.get('marca')} {carro.get('modelo')} (ID: {carro.get('id')})")
                pecas_instaladas = carro.get('pecas_instaladas', [])
                print(f"       Peças instaladas: {len(pecas_instaladas)}")
                for peca in pecas_instaladas:
                    print(f"         - {peca.get('nome')} ({peca.get('tipo')})")

            armazem = garagem.get('armazem', {})
            pecas_armazem = armazem.get('pecas_guardadas', [])
            print(f"   Peças no armazém: {len(pecas_armazem)}")
            for peca in pecas_armazem:
                print(f"     - {peca.get('nome')} ({peca.get('tipo')}) - Instalada: {peca.get('instalada', False)}")

            return garagem
        else:
            print(f"❌ Erro ao verificar garagem: {response.text}")
            return None
    except Exception as e:
        print(f"❌ Erro de conexão: {e}")
        return None

def main():
    print("🚀 Iniciando teste de sistema de compras...")
    print("=" * 60)

    # 1. Criar equipe
    equipe_id, senha = criar_equipe_teste()
    if not equipe_id:
        print("❌ Falha ao criar equipe. Abortando teste.")
        return

    time.sleep(1)

    # 2. Fazer login
    equipe_id_confirmado = fazer_login(equipe_id, senha)
    if not equipe_id_confirmado:
        print("❌ Falha no login. Abortando teste.")
        return

    time.sleep(1)

    # 3. Verificar garagem inicial
    print("\n📊 Garagem inicial:")
    verificar_garagem(equipe_id)

    # 4. Obter carros da loja
    carros_loja = obter_carros_loja(equipe_id)
    if not carros_loja:
        print("❌ Nenhum carro na loja. Abortando teste.")
        return

    # 5. Comprar primeiro carro disponível
    primeiro_carro = carros_loja[0]
    carro_id = primeiro_carro.get('id')
    variacao_id = None

    # Se o carro tem variações, usar a primeira
    if primeiro_carro.get('variacoes'):
        variacao_id = primeiro_carro['variacoes'][0].get('id')

    print(f"\n🛒 Comprando: {primeiro_carro.get('marca')} {primeiro_carro.get('modelo')}")
    sucesso = comprar_carro(equipe_id, carro_id, variacao_id)
    if not sucesso:
        print("❌ Falha ao comprar carro.")
    else:
        time.sleep(1)

    # 6. Verificar garagem após compra do carro
    print("\n📊 Garagem após compra do carro:")
    garagem = verificar_garagem(equipe_id)
    if not garagem or not garagem.get('carros'):
        print("❌ Nenhum carro na garagem após compra.")
        return

    # Obter ID do carro comprado
    carro_comprado = garagem['carros'][0]
    carro_comprado_id = carro_comprado.get('id')
    print(f"Carro comprado ID: {carro_comprado_id}")

    # 7. Obter peças da loja
    pecas_loja = obter_pecas_loja(equipe_id)
    if not pecas_loja:
        print("❌ Nenhuma peça na loja.")
        return

    # 8. Comprar primeira peça disponível
    primeira_peca = pecas_loja[0]
    peca_id = primeira_peca.get('id')

    print(f"\n🛒 Comprando peça: {primeira_peca.get('nome')} ({primeira_peca.get('tipo')})")
    sucesso = comprar_peca(equipe_id, peca_id, carro_comprado_id)
    if not sucesso:
        print("❌ Falha ao comprar peça.")
    else:
        time.sleep(1)

    # 9. Verificar garagem final
    print("\n📊 Garagem final após todas as compras:")
    garagem_final = verificar_garagem(equipe_id)

    # 10. Verificações finais
    print("\n🔍 Verificações finais:")

    if garagem_final and garagem_final.get('carros'):
        carros = garagem_final['carros']
        print(f"✅ Total de carros: {len(carros)}")

        for carro in carros:
            pecas_instaladas = carro.get('pecas_instaladas', [])
            print(f"   Carro {carro.get('marca')} {carro.get('modelo')}: {len(pecas_instaladas)} peças instaladas")

            # Verificar se a peça comprada está instalada
            peca_encontrada = False
            for peca in pecas_instaladas:
                if peca.get('nome') == primeira_peca.get('nome'):
                    peca_encontrada = True
                    print(f"   ✅ Peça '{peca.get('nome')}' encontrada no carro")
                    break

            if not peca_encontrada:
                print(f"   ❌ Peça '{primeira_peca.get('nome')}' NÃO encontrada no carro!")

    armazem = garagem_final.get('armazem', {})
    pecas_armazem = armazem.get('pecas_guardadas', [])
    print(f"✅ Peças no armazém: {len(pecas_armazem)}")

    print("\n🎉 Teste concluído!")

if __name__ == '__main__':
    main()