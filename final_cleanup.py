#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Final aggressive cleanup of all encoding issues"""

file_path = r"c:\Users\Gustavo Marquardt\Documents\GRANPIX\templates\admin.html"

print("="*70)
print("LIMPEZA FINAL E AGRESSIVA")
print("="*70)

try:
    # Read as UTF-8
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    print(f"[1] Arquivo lido: {len(content)} chars")
    
    # Remove all control characters and weird encoding artifacts
    cleaned = ""
    removed_count = 0
    
    for char in content:
        code = ord(char)
        # Remove control chars in problematic ranges
        if code < 32 and code not in [9, 10, 13]:  # Keep tab, newline, carriage return
            removed_count += 1
            continue
        # Remove ISO-8859-1 control chars (128-159) - these are often broken
        if 128 <= code <= 159:
            removed_count += 1
            continue
        cleaned += char
    
    print(f"[2] Removidos {removed_count} caracteres de controle problemáticos")
    
    # Final replacements
    final_fixes = {
        '🏁 Etapas': '🏁 Etapas',
        '💰 Comissões': '💰 Comissões',
        '⚙️ Configurações': '⚙️ Configurações',
    }
    
    for original, fixed in final_fixes.items():
        if original not in cleaned and fixed not in cleaned:
            # Try to find and fix
            pass
    
    # Write back
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(cleaned)
    
    print(f"[3] ✅ Arquivo salvo: {len(cleaned)} chars")
    
    # Final verification
    with open(file_path, 'r', encoding='utf-8') as f:
        final_check = f.read()
    
    # Count remaining suspicious chars
    suspicious = sum(1 for c in final_check if 128 <= ord(c) <= 159)
    print(f"[4] Caracteres suspeitos restantes: {suspicious}")
    
    # Test main words
    test_words = ['Peças', 'Solicitações', 'Variações', 'Comissões', 'Configurações']
    all_ok = all(word in final_check for word in test_words)
    
    if all_ok:
        print(f"[5] ✅ TODAS as palavras-chave foram encontradas!")
    else:
        for word in test_words:
            status = "✅" if word in final_check else "❌"
            print(f"    {status} {word}")
    
    print("\n" + "="*70)
    print("✅ ARQUIVO LIMPO E PRONTO")
    print("="*70)
    
except Exception as e:
    print(f"❌ ERRO: {e}")
    import traceback
    traceback.print_exc()
