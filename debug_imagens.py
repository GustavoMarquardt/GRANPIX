#!/usr/bin/env python3
"""
Script para debugar imagens no banco de dados
"""
import sys
sys.path.insert(0, '.')

from src.database import DatabaseManager
import base64

db = DatabaseManager()

# Carregar modelos
print("=" * 80)
print("DEBUGANDO IMAGENS DE CARROS")
print("=" * 80)

modelos = db.carregar_modelos_loja()
print(f"\nTotal de modelos: {len(modelos) if modelos else 0}")

if modelos:
    for modelo in modelos:
        print(f"\n[{modelo.id}] {modelo.marca} {modelo.modelo}")
        imagem = getattr(modelo, 'imagem', None)
        if imagem:
            print(f"  ✓ Tem imagem")
            print(f"  Tipo: {type(imagem)}")
            print(f"  Tamanho: {len(imagem)} caracteres" if isinstance(imagem, str) else f"  Tamanho: {len(imagem)} bytes")
            
            # Mostrar primeiros caracteres
            if isinstance(imagem, str):
                preview = imagem[:100]
                print(f"  Preview: {preview}")
                
                # Verificar se é válido
                if imagem.startswith('data:image'):
                    print(f"  ✓ Tem prefixo data:image correto")
                    # Tentar extrair o base64
                    base64_part = imagem.split(',', 1)[1] if ',' in imagem else ''
                    if base64_part:
                        print(f"  ✓ Base64 extraído: {len(base64_part)} caracteres")
                else:
                    print(f"  ✗ NÃO tem prefixo data:image")
            else:
                print(f"  ✗ Imagem é bytes, não string!")
        else:
            print(f"  ✗ SEM IMAGEM")

print("\n" + "=" * 80)
print("DEBUGANDO IMAGENS DE PEÇAS")
print("=" * 80)

pecas = db.carregar_pecas_loja()
print(f"\nTotal de peças: {len(pecas) if pecas else 0}")

if pecas:
    for peca in pecas:
        imagem = getattr(peca, 'imagem', None)
        if imagem:
            print(f"\n[{peca.id}] {peca.nome}")
            print(f"  ✓ Tem imagem")
            print(f"  Tipo: {type(imagem)}")
            print(f"  Tamanho: {len(imagem)} caracteres" if isinstance(imagem, str) else f"  Tamanho: {len(imagem)} bytes")
            
            if isinstance(imagem, str):
                preview = imagem[:100]
                print(f"  Preview: {preview}")
                
                if imagem.startswith('data:image'):
                    print(f"  ✓ Tem prefixo data:image correto")
                else:
                    print(f"  ✗ NÃO tem prefixo data:image")

print("\n" + "=" * 80)
print("FIM DO DEBUG")
print("=" * 80)
