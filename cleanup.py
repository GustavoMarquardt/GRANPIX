import re

with open('templates/admin.html', 'r', encoding='utf-8') as f:
    content = f.read()

# LIMPEZA TOTAL DE ESPAÇOS
lines = []
for line in content.split('\n'):
    if line.strip():
        line_content = line.strip()
        if line[0] == ' ':
            lines.append('  ' + line_content)
        else:
            lines.append(line_content)

content = '\n'.join(lines)

# Não deixar mais de 1 linha em branco seguida
while '\n\n\n' in content:
    content = content.replace('\n\n\n', '\n\n')

# Corrigir caracteres quebrados
fixes = {
    'SolicitaÃ§ÃÃµes': 'Solicitações',
    'SolicitaÃ§Ã£o': 'Solicitação',
    'VariaÃ§ÃÃµes': 'Variações',
    'VariaÃ§Ã£o': 'Variação',
    'ComissÃÃµes': 'Comissões',
    'ConfiguraÃ§ÃÃµes': 'Configurações',
    'PeÃ§a': 'Peça',
    'PeÃ§as': 'Peças',
    'PreÃÃÃ§o': 'Preço',
    'CÃ¢mbio': 'Câmbio',
    'CÃÃmbios': 'Câmbios',
    'SuspensÃ£o': 'Suspensão',
    'DisponÃ­veis': 'Disponíveis',
    'NÃÃºmero': 'Número',
    'Nûmero': 'Número',
    'SÃ©rie': 'Série',
}

for old, new in fixes.items():
    content = content.replace(old, new)

with open('templates/admin.html', 'w', encoding='utf-8') as f:
    f.write(content)

lines_final = len(content.split('\n'))
size_final = len(content)
print(f'OK!')
print(f'Tamanho: {size_final} bytes')
print(f'Linhas: {lines_final}')
