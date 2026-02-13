"""
Integração com MercadoPago para gerar QR Codes PIX
"""

import requests
import json
import uuid
import base64
import io
from src.mercado_pago_config import (
    MERCADO_PAGO_ACCESS_TOKEN, 
    TAXA_PERCENTUAL, 
    TAXA_FIXA, 
    DESCRICAO_PADRAO
)

try:
    import qrcode
    HAS_QRCODE = True
except ImportError:
    HAS_QRCODE = False
    print("[AVISO] Biblioteca qrcode não instalada")

class MercadoPagoIntegracao:
    def __init__(self):
        self.access_token = MERCADO_PAGO_ACCESS_TOKEN
        self.taxa_percentual = TAXA_PERCENTUAL
        self.taxa_fixa = TAXA_FIXA
        self.base_url = "https://api.mercadopago.com/v1"
        self.headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
            "X-Idempotency-Key": str(uuid.uuid4())
        }
    
    def calcular_taxa(self, valor: float) -> float:
        """Calcula a taxa a ser adicionada ao valor com arredondamento correto"""
        if self.taxa_percentual > 0:
            taxa_perc = valor * (self.taxa_percentual / 100)
        else:
            taxa_perc = 0
        
        # Arredondar para 2 casas decimais (centavos)
        taxa_total = round(taxa_perc + self.taxa_fixa, 2)
        return taxa_total
    
    def gerar_qr_code_imagem_pix(self, codigo_pix: str) -> str:
        """
        Gera uma imagem QR code a partir do código PIX
        
        Args:
            codigo_pix: String do PIX Copia e Cola
        
        Returns:
            String base64 da imagem PNG do QR code
        """
        if not HAS_QRCODE:
            print("[AVISO] qrcode não disponível, tentando API externa...")
            return self.gerar_qr_code_api_externa(codigo_pix)
        
        try:
            # Criar QR code
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_L,
                box_size=10,
                border=4,
            )
            qr.add_data(codigo_pix)
            qr.make(fit=True)
            
            # Criar imagem
            img = qr.make_image(fill_color="black", back_color="white")
            
            # Converter para base64
            buffer = io.BytesIO()
            img.save(buffer, format='PNG')
            img_base64 = base64.b64encode(buffer.getvalue()).decode()
            
            return img_base64
        except Exception as e:
            print(f"[ERRO] Erro ao gerar imagem QR code: {e}")
            print("[AVISO] Tentando API externa...")
            return self.gerar_qr_code_api_externa(codigo_pix)
    
    def gerar_qr_code_api_externa(self, codigo_pix: str) -> str:
        """
        Gera QR code usando API externa como fallback
        """
        try:
            import urllib.parse
            # Usar qr-server.com que é gratuita e não precisa de API key
            data_encoded = urllib.parse.quote(codigo_pix)
            url_api = f"https://api.qrserver.com/v1/create-qr-code/?size=300x300&data={data_encoded}"
            
            print(f"[QR API] Obtendo QR code de {url_api[:50]}...")
            
            response = requests.get(url_api, timeout=5)
            if response.status_code == 200:
                img_base64 = base64.b64encode(response.content).decode()
                print(f"[QR API] QR code obtido com sucesso ({len(img_base64)} caracteres)")
                return img_base64
            else:
                print(f"[QR API ERRO] Status {response.status_code}")
                return None
        except Exception as e:
            print(f"[QR API ERRO] {e}")
            return None
    
    def gerar_qr_code_pix(self, descricao: str, valor: float, referencia: str = None) -> dict:
        """
        Gera um QR Code PIX usando MercadoPago
        
        Args:
            descricao: Descrição da transação
            valor: Valor em reais
            referencia: ID da transação para rastreamento
        
        Returns:
            {'sucesso': bool, 'qr_code': str, 'qr_code_url': str, 'id': str, 'erro': str}
        """
        try:
            # Payload para criar uma ordem de pagamento com PIX
            payload = {
                "description": descricao or DESCRICAO_PADRAO,
                "external_reference": referencia or "",
                "transaction_amount": valor,
                "payment_method_id": "pix",
                "payer": {
                    "email": "comprador@granpix.com"
                }
            }
            
            print(f"[MP DEBUG] Enviando requisição para {self.base_url}/payments")
            print(f"[MP DEBUG] Token: {self.access_token[:30]}...")
            print(f"[MP DEBUG] Payload: {json.dumps(payload, indent=2)}")
            
            # Criar headers com Idempotency Key único para essa transação
            headers = self.headers.copy()
            headers["X-Idempotency-Key"] = str(uuid.uuid4())
            
            # Criar pagamento PIX no MercadoPago
            response = requests.post(
                f"{self.base_url}/payments",
                headers=headers,
                json=payload,
                timeout=10
            )
            
            print(f"[MP DEBUG] Status: {response.status_code}")
            print(f"[MP DEBUG] Response: {response.text[:1000]}")
            
            if response.status_code in [200, 201]:
                payment_data = response.json()
                
                # Extrair dados do QR Code PIX
                qr_code = None
                qr_code_url = None
                
                print(f"[MP DEBUG] Resposta recebida com sucesso (status {response.status_code})")
                print(f"[MP DEBUG] Tipo de dados: {type(payment_data)}")
                print(f"[MP DEBUG] Chaves da resposta: {list(payment_data.keys())}")
                
                # Debug: imprimir estrutura completa (primeiros 3000 caracteres)
                resp_str = json.dumps(payment_data, indent=2, ensure_ascii=False)
                print(f"[MP DEBUG] Resposta completa:\n{resp_str[:3000]}")
                
                # Verificar estrutura de retorno do MercadoPago
                if "point_of_interaction" in payment_data:
                    poi = payment_data["point_of_interaction"]
                    print(f"[MP DEBUG] point_of_interaction encontrado: {list(poi.keys())}")
                    if "transaction_data" in poi:
                        qr_code = poi["transaction_data"].get("qr_code")
                        qr_code_url = poi["transaction_data"].get("qr_code_url")
                        print(f"[MP DEBUG] QR Code extraído: {qr_code[:50] if qr_code else 'None'}...")
                        print(f"[MP DEBUG] QR Code URL: {qr_code_url}")
                
                # Verificar também em 'charges'
                if not qr_code and "charges" in payment_data:
                    print(f"[MP DEBUG] Verificando charges...")
                    for charge in payment_data.get("charges", []):
                        if charge.get("payment_method") == "pix":
                            qr_data = charge.get("payment_method_details", {})
                            qr_code = qr_data.get("pix_qr_code")
                            qr_code_url = qr_data.get("qr_code_url")
                            print(f"[MP DEBUG] QR Code encontrado em charges")
                            break
                
                # Fallback: se não tiver QR code, usar dados do pagamento
                if not qr_code and "id" in payment_data:
                    qr_code = f"PIX_{payment_data.get('id', '')}"
                    print(f"[MP DEBUG] Usando fallback: {qr_code}")
                
                print(f"[MP] Pagamento criado com sucesso - ID: {payment_data.get('id')}")
                print(f"[MP] QR Code final: {qr_code[:50] if qr_code else 'None'}...")
                print(f"[MP] QR Code URL final: {qr_code_url}")
                
                # Se temos o código PIX em texto, gerar imagem QR code
                if qr_code and not qr_code.startswith('data:') and not qr_code_url:
                    print(f"[MP] Gerando imagem QR code a partir do código PIX...")
                    img_base64 = self.gerar_qr_code_imagem_pix(qr_code)
                    if img_base64:
                        qr_code_url = f"data:image/png;base64,{img_base64}"
                        print(f"[MP] Imagem QR code gerada com sucesso ({len(img_base64)} caracteres)")
                    else:
                        print(f"[MP] Falha ao gerar imagem, usando código PIX como fallback")
                
                return {
                    'sucesso': True,
                    'qr_code': qr_code,
                    'qr_code_url': qr_code_url or "",
                    'id': payment_data.get('id', ''),
                    'checkout_url': ""
                }
            elif response.status_code == 400:
                # Bad request - pode ser token inválido ou parâmetros incorretos
                error_msg = f"Requisição inválida: {response.text}"
                print(f"[MP ERRO] {error_msg}")
                return {
                    'sucesso': False,
                    'erro': error_msg
                }
            elif response.status_code == 401:
                error_msg = "Token MercadoPago inválido ou expirado"
                print(f"[MP ERRO] {error_msg}")
                return {
                    'sucesso': False,
                    'erro': error_msg
                }
            else:
                error_msg = f"Erro MercadoPago: {response.status_code} - {response.text}"
                print(f"[MP ERRO] {error_msg}")
                return {
                    'sucesso': False,
                    'erro': error_msg
                }
        
        except requests.exceptions.Timeout:
            error_msg = "Timeout ao conectar com MercadoPago"
            print(f"[MP ERRO] {error_msg}")
            return {
                'sucesso': False,
                'erro': error_msg
            }
        except requests.exceptions.ConnectionError as e:
            error_msg = f"Erro de conexão com MercadoPago: {e}"
            print(f"[MP ERRO] {error_msg}")
            return {
                'sucesso': False,
                'erro': error_msg
            }
        except Exception as e:
            import traceback
            error_msg = f"Erro ao gerar QR Code PIX: {e}"
            print(f"[ERRO MP] {error_msg}")
            traceback.print_exc()
            return {
                'sucesso': False,
                'erro': error_msg
            }
    
    def obter_pagamento(self, payment_id: str) -> dict:
        """Obtém informações de um pagamento"""
        try:
            headers = self.headers.copy()
            headers["X-Idempotency-Key"] = str(uuid.uuid4())
            
            response = requests.get(
                f"{self.base_url}/payments/{payment_id}",
                headers=headers
            )
            return response.json()
        except Exception as e:
            print(f"[ERRO MP] Erro ao obter pagamento: {e}")
            return {}
    
    def processar_webhook(self, dados: dict) -> dict:
        """
        Processa webhook recebido do MercadoPago
        
        Exemplo de dados recebidos:
        {
            'id': '1234567890',
            'topic': 'payment',
            'resource': '/v1/payments/1234567890'
        }
        """
        try:
            topic = dados.get('topic')
            resource_id = dados.get('id')
            
            if topic == 'payment':
                # Buscar detalhes do pagamento
                payment = self.obter_pagamento(resource_id)
                
                status = payment.get('status')
                external_reference = payment.get('external_reference', '')
                
                return {
                    'sucesso': True,
                    'status': status,
                    'transacao_id': external_reference,
                    'payment_id': resource_id
                }
            
            return {'sucesso': False, 'erro': 'Topic desconhecido'}
        
        except Exception as e:
            print(f"[ERRO MP] Erro ao processar webhook: {e}")
            return {'sucesso': False, 'erro': str(e)}


# Instância global
mp_client = MercadoPagoIntegracao()
