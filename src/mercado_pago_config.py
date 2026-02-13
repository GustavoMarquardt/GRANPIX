"""
Configuração do MercadoPago para integração PIX
"""

import os

# Tentar carregar do arquivo .env se existir
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    print("[AVISO] python-dotenv não instalado, usando variáveis de ambiente do sistema")
    pass

# Token de acesso do MercadoPago
MERCADO_PAGO_ACCESS_TOKEN = os.getenv('MERCADO_PAGO_ACCESS_TOKEN', 'APP_USR-3239640550465416-020202-53c31fcd234dda4ef5e83b0bf49a6af9-284990230')

# URL da sua aplicação (use localhost para testes)
WEBHOOK_URL = os.getenv('WEBHOOK_URL', 'http://localhost:5000/api/webhook/mercado-pago')

# Percentual de taxa adicionado ao pagamento (0 = sem taxa extra, 5 = 5%)
# MercadoPago cobra 1% de taxa no PIX
TAXA_PERCENTUAL = float(os.getenv('TAXA_PERCENTUAL', 1))

# Taxa fixa em reais (0 = sem taxa fixa)
TAXA_FIXA = float(os.getenv('TAXA_FIXA', 0))

# Descrição padrão das transações
DESCRICAO_PADRAO = "Compra no sistema GRANPIX"

print(f"[CONFIG] MercadoPago configurado com token: {MERCADO_PAGO_ACCESS_TOKEN[:20]}...")
