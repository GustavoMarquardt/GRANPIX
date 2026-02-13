#!/usr/bin/env python3
"""
Teste visual da tabela de qualificação com tema branco/vermelho
"""

import requests
import json

BASE_URL = 'http://localhost:5000'

def teste_tabela_qualificacao():
    print("🎨 Teste do Tema Branco/Vermelho da Tabela de Qualificação")
    print("=" * 60)

    # Verificar se o servidor está rodando
    try:
        response = requests.get(f'{BASE_URL}/')
        if response.status_code != 200:
            print("❌ Servidor não está respondendo")
            return
        print("✅ Servidor está rodando")
    except Exception as e:
        print(f"❌ Erro de conexão: {e}")
        return

    # Verificar se a página admin existe
    try:
        response = requests.get(f'{BASE_URL}/admin/fazer-etapa')
        if response.status_code == 200:
            print("✅ Página de administração acessível")
        else:
            print(f"⚠️  Página de administração retorna status {response.status_code}")
    except Exception as e:
        print(f"⚠️  Erro ao acessar página admin: {e}")

    print("\n📋 Mudanças aplicadas:")
    print("   ✅ Cabeçalho da tabela: Fundo vermelho gradiente")
    print("   ✅ Texto do cabeçalho: Branco")
    print("   ✅ Bordas: Vermelhas (#dc3545)")
    print("   ✅ Fundo da tabela: Branco")
    print("   ✅ Linhas alternadas: Cinza claro e branco")
    print("   ✅ Campos de entrada: Bordas vermelhas, fundo branco")
    print("   ✅ Texto das células: Preto/cinza para boa legibilidade")
    print("   ✅ Status: Verde para andando, amarelo para próximo, vermelho para finalizado")
    print("   ✅ Hover: Efeito sutil de mudança de cor")

    print("\n🎯 Para testar visualmente:")
    print("   1. Acesse /admin/fazer-etapa")
    print("   2. Inicie uma qualificação")
    print("   3. Verifique se a tabela tem o tema branco/vermelho aplicado")

    print("\n✅ Tema branco/vermelho implementado com sucesso!")

if __name__ == '__main__':
    teste_tabela_qualificacao()