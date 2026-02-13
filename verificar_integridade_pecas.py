#!/usr/bin/env python3
import mysql.connector
from mysql.connector import Error

def verificar_integridade():
    try:
        conn = mysql.connector.connect(
            host="localhost",
            user="root",
            password="1234",
            database="granpix"
        )
        cursor = conn.cursor(dictionary=True)

        print("VERIFICAÇÃO DE INTEGRIDADE DAS PEÇAS DOS CARROS")
        print("=" * 80)

        # Pegar todos os carros e suas peças
        cursor.execute("""
            SELECT c.id, c.modelo, c.nome_carro, p.nome, p.peca_loja_id, p.id
            FROM carros c
            LEFT JOIN pecas p ON c.id = p.carro_id
            ORDER BY c.nome_carro, p.tipo
        """)
        
        carros = {}
        for row in cursor.fetchall():
            carro_id = row['id']
            if carro_id not in carros:
                carros[carro_id] = {
                    'nome': row['nome_carro'],
                    'modelo': row['modelo'],
                    'pecas': []
                }
            if row['nome']:
                carros[carro_id]['pecas'].append({
                    'nome': row['nome'],
                    'peca_loja_id': row['peca_loja_id'],
                    'id': row['id']
                })

        # Agora verificar se as peças são as corretas do modelo
        cursor.execute("SELECT id FROM modelos_carro_loja ORDER BY nome")
        modelos = {row['id']: row['id'] for row in cursor.fetchall()}

        issues = []
        for carro_id, carro_info in carros.items():
            # Pegar modelo esperado
            cursor.execute("""
                SELECT motor_id, cambio_id 
                FROM modelos_carro_loja 
                WHERE id = %s
            """, (carro_info['modelo'],))
            
            modelo = cursor.fetchone()
            if modelo:
                motor_id = modelo['motor_id']
                cambio_id = modelo['cambio_id']
                
                # Verificar peças
                pecas_motor = [p for p in carro_info['pecas'] if 'motor' in p['nome'].lower() or p['peca_loja_id'] == motor_id]
                pecas_cambio = [p for p in carro_info['pecas'] if 'cambio' in p['nome'].lower() or p['peca_loja_id'] == cambio_id]
                
                if not pecas_motor:
                    issues.append(f"❌ {carro_info['nome']}: SEM MOTOR")
                elif motor_id not in [p['peca_loja_id'] for p in pecas_motor]:
                    issues.append(f"❌ {carro_info['nome']}: MOTOR INCORRETO ({pecas_motor[0]['nome']} ao invés do esperado)")
                
                if not pecas_cambio:
                    issues.append(f"❌ {carro_info['nome']}: SEM CÂMBIO")
                elif cambio_id not in [p['peca_loja_id'] for p in pecas_cambio]:
                    issues.append(f"❌ {carro_info['nome']}: CÂMBIO INCORRETO ({pecas_cambio[0]['nome']} ao invés do esperado)")

        if issues:
            print("\n⚠️  PROBLEMAS ENCONTRADOS:\n")
            for issue in issues:
                print(f"  {issue}")
        else:
            print("\n✅ TODAS AS PEÇAS DOS CARROS ESTÃO CORRETAS!")

        print("\n" + "=" * 80)
        cursor.close()

    except Error as e:
        print(f"Erro na conexão: {e}")

if __name__ == "__main__":
    verificar_integridade()
