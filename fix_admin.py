#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Ler arquivo com encoding latin-1 (que suporta mais caracteres)
with open('templates/admin.html', 'r', encoding='latin-1') as f:
    lines = f.readlines()

# Remover as últimas linhas que adicionei (aquelas com 'Carregar script.js')
new_lines = []
for i, line in enumerate(lines):
    # Parar antes de qualquer linha que contenha 'Carregar script'
    if 'Carregar script' in line:
        break
    new_lines.append(line)

# Agora temos o arquivo sem as linhas problemáticas
content = ''.join(new_lines).rstrip()

# Agora adicionar o script.js de forma limpa
content += '\n\n    <!-- Carregar script.js para funcoes de admin -->\n'
content += '    <script src="{{ url_for(\'static\', filename=\'script.js\') }}"></script>\n'
content += '</body>\n\n</html>'

# Escrever em UTF-8 puro
with open('templates/admin.html', 'w', encoding='utf-8') as f:
    f.write(content)

print(f'Arquivo corrigido! Total de linhas: {len(new_lines)}')
print('Pronto para uso!')
