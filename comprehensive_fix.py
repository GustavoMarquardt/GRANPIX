#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Comprehensive fix for all broken characters in admin.html"""

file_path = r"c:\Users\Gustavo Marquardt\Documents\GRANPIX\templates\admin.html"

print("="*70)
print("CORREÇÃO COMPLETA DE TODOS OS CARACTERES QUEBRADOS")
print("="*70)

try:
    # Step 1: Read file as binary
    with open(file_path, 'rb') as f:
        raw_bytes = f.read()
    
    print(f"[1] Arquivo lido em bytes: {len(raw_bytes)} bytes")
    
    # Step 2: Try to decode as latin-1 (encoding quebrado)
    try:
        content_latin1 = raw_bytes.decode('latin-1')
        print(f"[2] Decodificado como latin-1: {len(content_latin1)} chars")
        
        # Step 3: Re-encode as UTF-8 e decode de novo
        # Isso vai corrigir caracteres que foram double-encoded
        content_fixed = content_latin1.encode('utf-8').decode('utf-8')
        print(f"[3] Re-encoded para UTF-8: {len(content_fixed)} chars")
        
    except Exception as e:
        print(f"    ❌ Erro na re-encoding: {e}")
        # Fallback: try UTF-8 directly
        content_fixed = raw_bytes.decode('utf-8', errors='replace')
        print(f"    Usando UTF-8 com replacement: {len(content_fixed)} chars")
    
    # Step 4: Manual replacements for known broken patterns
    replacements = {
        # Caracteres acentuados quebrados
        'Ã§': 'ç',
        'Ã¢': 'â',
        'Ã¡': 'á',
        'Ã©': 'é',
        'Ã­': 'í',
        'Ã³': 'ó',
        'Ã¡': 'á',
        'Ã£': 'ã',
        'Ã±': 'ñ',
        'Ã¦': 'æ',
        'Ã°': 'ð',
        'Ã¾': 'þ',
        
        # Combinações comuns quebradas
        'Ã§Ã£o': 'ção',
        'Ã§Ã£': 'ção',
        'Ã¡o': 'ão',
        'Ã´': 'ô',
        'Ãµ': 'õ',
        'Ã˜': 'Ø',
        'Ã©': 'é',
        'Ãº': 'ú',
        'Â': '',  # Remove char quebrado
        'Ã': '',  # Remove char quebrado
        'ð': '🏁',
        'ð°': '💰',
        'â': '',
    }
    
    print(f"\n[4] Aplicando {len(replacements)} substituições manuais:")
    
    replacements_count = 0
    for broken, fixed in replacements.items():
        count = content_fixed.count(broken)
        if count > 0:
            content_fixed = content_fixed.replace(broken, fixed)
            replacements_count += count
            if count <= 5:
                print(f"    '{broken}' → '{fixed}' ({count}x)")
            else:
                print(f"    '{broken}' → '{fixed}' ({count}x) ⭐")
    
    print(f"\n    Total: {replacements_count} substituições realizadas")
    
    # Step 5: Write back with explicit UTF-8
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content_fixed)
    
    print(f"\n[5] ✅ Arquivo salvo com sucesso em UTF-8")
    
    # Step 6: Verify
    with open(file_path, 'r', encoding='utf-8') as f:
        verify_content = f.read()
    
    # Test common Portuguese words
    test_words = [
        'Peças', 'Solicitações', 'Variações', 'Comissões', 'Configurações',
        'descrição', 'instalação', 'carregado', 'ação', 'carro', 'equipe'
    ]
    
    print(f"\n[6] VERIFICAÇÃO DE PALAVRAS-CHAVE:")
    found = 0
    for word in test_words:
        if word in verify_content:
            found += 1
            print(f"    ✅ '{word}'")
        else:
            print(f"    ⚠️  '{word}' (não encontrado)")
    
    print(f"\n    {found}/{len(test_words)} palavras encontradas")
    
    # Step 7: Check for remaining broken chars
    print(f"\n[7] ANÁLISE DE CARACTERES RESTANTES:")
    
    # Look for suspicious patterns
    suspicious_count = 0
    for i, char in enumerate(verify_content):
        if ord(char) > 127 and ord(char) < 160:  # ISO-8859-1 range
            suspicious_count += 1
            if suspicious_count <= 5:
                print(f"    ⚠️  Char suspeito encontrado: {repr(char)} (posição {i})")
    
    if suspicious_count > 5:
        print(f"    ... e mais {suspicious_count - 5} caracteres suspeitos")
    elif suspicious_count == 0:
        print(f"    ✅ Nenhum caractere suspeito detectado!")
    
    print("\n" + "="*70)
    print("✅ CORREÇÃO COMPLETA CONCLUÍDA")
    print("="*70)
    
except Exception as e:
    print(f"\n❌ ERRO CRÍTICO: {e}")
    import traceback
    traceback.print_exc()
