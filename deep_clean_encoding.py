#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Deep clean of admin.html encoding"""

file_path = r"c:\Users\Gustavo Marquardt\Documents\GRANPIX\templates\admin.html"

print("="*60)
print("LIMPEZA PROFUNDA DE ENCODING - admin.html")
print("="*60)

try:
    # Step 1: Read file as binary to check for BOM
    with open(file_path, 'rb') as f:
        raw_bytes = f.read()
    
    print(f"\n[1] Arquivo em bytes: {len(raw_bytes)} bytes")
    print(f"    Primeiros 10 bytes: {raw_bytes[:10]}")
    
    # Check for BOM
    if raw_bytes.startswith(b'\xef\xbb\xbf'):
        print("    ⚠️  BOM UTF-8 detectado, removendo...")
        raw_bytes = raw_bytes[3:]
    elif raw_bytes.startswith(b'\xff\xfe'):
        print("    ⚠️  BOM UTF-16 LE detectado")
    elif raw_bytes.startswith(b'\xfe\xff'):
        print("    ⚠️  BOM UTF-16 BE detectado")
    else:
        print("    ✅ Sem BOM detectado")
    
    # Step 2: Try to decode as UTF-8
    try:
        content = raw_bytes.decode('utf-8')
        print(f"[2] Decodificado com sucesso como UTF-8: {len(content)} chars")
    except Exception as e:
        print(f"    ❌ Erro ao decodificar UTF-8: {e}")
        # Try latin-1 as fallback
        content = raw_bytes.decode('latin-1')
        print(f"    Tentando latin-1: {len(content)} chars")
    
    # Step 3: Ensure correct meta charset
    if '<meta charset="UTF-8">' in content:
        print("[3] ✅ Meta charset UTF-8 encontrado")
    else:
        print("[3] ⚠️  Meta charset não encontrado ou incorreto")
        # Add it if missing
        if '<head>' in content:
            content = content.replace('<head>', '<head>\n    <meta charset="UTF-8">')
            print("    Adicionado meta charset")
    
    # Step 4: Clean up the HTML
    # Remove any weird characters at the start
    content = content.lstrip()
    
    print(f"[4] Conteúdo limpo: {len(content)} chars")
    
    # Step 5: Write back as pure UTF-8 (no BOM)
    with open(file_path, 'w', encoding='utf-8', newline='') as f:
        f.write(content)
    
    print("[5] ✅ Arquivo escrito com sucesso em UTF-8 puro (sem BOM)")
    
    # Step 6: Verify
    with open(file_path, 'rb') as f:
        verify_bytes = f.read()
    
    if verify_bytes.startswith(b'\xef\xbb\xbf'):
        print("[6] ⚠️  BOM ainda presente após write")
    else:
        print("[6] ✅ Verificação: Sem BOM, UTF-8 puro")
    
    print("\n" + "="*60)
    print("TESTE DE DECODIFICAÇÃO")
    print("="*60)
    
    # Test specific words
    with open(file_path, 'r', encoding='utf-8') as f:
        test_content = f.read()
    
    test_words = ['Peças', 'Solicitações', 'Variações', 'Comissões', 'Configurações']
    for word in test_words:
        if word in test_content:
            print(f"✅ '{word}' encontrado e correto")
        else:
            print(f"❌ '{word}' NÃO encontrado")
    
    print("\n" + "="*60)
    print("CONCLUÍDO COM SUCESSO")
    print("="*60)
    
except Exception as e:
    print(f"\n❌ ERRO: {e}")
    import traceback
    traceback.print_exc()
