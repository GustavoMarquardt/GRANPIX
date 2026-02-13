#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Rebuild admin.html with proper UTF-8 encoding"""

import os

file_path = r"c:\Users\Gustavo Marquardt\Documents\GRANPIX\templates\admin.html"

print(f"Reading file: {file_path}")

try:
    # Try reading with latin-1
    with open(file_path, 'r', encoding='latin-1') as f:
        content = f.read()
    
    print(f"✅ Successfully read with latin-1 encoding")
    print(f"Content length: {len(content)} characters")
    
    # Ensure correct script.js reference at end
    # Remove old script reference if it exists
    if '<script src="{{ url_for' in content:
        # Find and remove the script tag
        start = content.rfind('<script src="{{ url_for')
        if start != -1:
            end = content.find('</script>', start)
            if end != -1:
                content = content[:start] + content[end+9:]
                print("✅ Removed old script tag")
    
    # Make sure script tag exists before closing body
    if '</body>' in content:
        script_tag = '    <!-- Carregar script.js para funções de admin (campeonatos, etapas, etc) -->\n    <script src="{{ url_for(\'static\', filename=\'script.js\') }}"></script>\n'
        content = content.replace('</body>', script_tag + '</body>')
        print("✅ Ensured script.js reference in body")
    
    # Write with UTF-8 encoding
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print(f"✅ Successfully written with UTF-8 encoding")
    
    # Verify it can be read back
    with open(file_path, 'r', encoding='utf-8') as f:
        verify = f.read()
    
    print(f"✅ Verification: File can be read back as UTF-8 ({len(verify)} characters)")
    
    # Check for any special characters
    special_chars = [c for c in verify if ord(c) > 127]
    if special_chars:
        print(f"⚠️ File contains {len(special_chars)} non-ASCII characters (normal for Portuguese)")
    
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
