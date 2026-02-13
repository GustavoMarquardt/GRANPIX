#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Fix broken Portuguese characters in admin.html"""

import re

file_path = r"c:\Users\Gustavo Marquardt\Documents\GRANPIX\templates\admin.html"

# Mapa de caracteres quebrados → caracteres corretos
broken_chars = {
    'PeÃ§as': 'Peças',
    'PeÃ§a': 'Peça',
    'SolicitaÃ§Ãµes': 'Solicitações',
    'SolicitaÃ§Ã£o': 'Solicitação',
    'VariaÃ§Ãµes': 'Variações',
    'ComissÃµes': 'Comissões',
    'ConfiguraÃ§Ãµes': 'Configurações',
    'prea': 'preço',
    'descriÃ§Ã£o': 'descrição',
    'duraÃ§Ã£o': 'durabilidade',
    'instalaÃ§Ã£o': 'instalação',
    'DiferÃªncial': 'Diferencial',
    'â': '',  # Remove broken emoji chars
    'ð': '🏁',  # Try to fix emoji
    'ð°': '💰',  # Try to fix emoji
    'âï¸': '⚙️',  # Try to fix emoji
}

print("="*60)
print("CORRIGINDO CARACTERES PORTUGUESES QUEBRADOS")
print("="*60)

try:
    # Read file as UTF-8
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    print(f"[1] Arquivo lido: {len(content)} chars")
    
    # Count replacements
    replacements_made = 0
    
    # Apply replacements
    for broken, fixed in broken_chars.items():
        count = content.count(broken)
        if count > 0:
            content = content.replace(broken, fixed)
            replacements_made += count
            print(f"    ✅ '{broken}' → '{fixed}' ({count}x)")
    
    print(f"\n[2] Total de substituições: {replacements_made}")
    
    # Additional fixes for common patterns
    # Fix case where chars got split weird
    patterns = [
        (r'Pea\?as', 'Peças'),
        (r'Solicita\?oes', 'Solicitações'),
        (r'Varia\?oes', 'Variações'),
        (r'Comiss\?oes', 'Comissões'),
        (r'Configura\?oes', 'Configurações'),
    ]
    
    for pattern, replacement in patterns:
        matches = re.findall(pattern, content)
        if matches:
            content = re.sub(pattern, replacement, content)
            print(f"    ✅ Pattern '{pattern}' → '{replacement}'")
    
    # Write back
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print(f"\n[3] Arquivo salvo com sucesso em UTF-8")
    
    # Verify
    with open(file_path, 'r', encoding='utf-8') as f:
        verify = f.read()
    
    test_words = ['Peças', 'Solicitações', 'Variações', 'Comissões', 'Configurações']
    print(f"\n[4] VERIFICAÇÃO:")
    for word in test_words:
        if word in verify:
            print(f"    ✅ '{word}' encontrado")
        else:
            print(f"    ❌ '{word}' NÃO encontrado")
    
    print("\n" + "="*60)
    print("CONCLUÍDO")
    print("="*60)
    
except Exception as e:
    print(f"❌ ERRO: {e}")
    import traceback
    traceback.print_exc()
