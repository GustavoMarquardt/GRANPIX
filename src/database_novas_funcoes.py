# NOVAS FUNÇÕES PARA CONFIRMAÇÃO DE PARTICIPAÇÃO

def obter_pilotos_para_confirmacao(self, etapa_id: str) -> dict:
    """Retorna pilotos que precisam confirmar participação (1h antes da etapa)"""
    try:
        conn = self._get_conn()
        cursor = conn.cursor(dictionary=True)
        
        # Buscar etapa e calcular tempo de confirmação (1h antes)
        cursor.execute('''
            SELECT id, data_etapa, hora_etapa FROM etapas
            WHERE id = %s
        ''', (etapa_id,))
        
        etapa = cursor.fetchone()
        if not etapa:
            cursor.close()
            conn.close()
            return {'sucesso': False, 'erro': 'Etapa não encontrada'}
        
        # Buscar pilotos que estão em participacoes_etapas mas sem confirmação
        cursor.execute('''
            SELECT 
                pe.id as participacao_id,
                pe.piloto_id,
                pi.nome as piloto_nome,
                pe.equipe_id,
                e.nome as equipe_nome,
                pe.status
            FROM participacoes_etapas pe
            INNER JOIN pilotos pi ON pe.piloto_id = pi.id
            INNER JOIN equipes e ON pe.equipe_id = e.id
            WHERE pe.etapa_id = %s 
              AND pe.piloto_id IS NOT NULL 
              AND pe.status IN ('inscrita', 'pendente')
            ORDER BY pe.data_inscricao ASC
        ''', (etapa_id,))
        
        pilotos = cursor.fetchall()
        cursor.close()
        conn.close()
        
        return {
            'sucesso': True,
            'pilotos': pilotos or [],
            'data_etapa': str(etapa['data_etapa']),
            'hora_etapa': str(etapa['hora_etapa'])
        }
    except Exception as e:
        print(f"[DB] Erro ao obter pilotos para confirmação: {e}")
        import traceback
        traceback.print_exc()
        return {'sucesso': False, 'erro': str(e), 'pilotos': []}

def confirmar_participacao_piloto(self, participacao_id: str, piloto_id: str) -> dict:
    """Piloto confirma que vai andar na etapa"""
    try:
        conn = self._get_conn()
        cursor = conn.cursor(dictionary=True)
        
        # Verificar se participação existe
        cursor.execute('''
            SELECT etapa_id, equipe_id, piloto_id FROM participacoes_etapas
            WHERE id = %s
        ''', (participacao_id,))
        
        participacao = cursor.fetchone()
        if not participacao:
            cursor.close()
            conn.close()
            return {'sucesso': False, 'erro': 'Participação não encontrada'}
        
        # Verificar se piloto é o correto
        if participacao['piloto_id'] != piloto_id:
            cursor.close()
            conn.close()
            return {'sucesso': False, 'erro': 'Piloto não autorizado para confirmar'}
        
        # Atualizar status para 'confirmado'
        cursor.execute('''
            UPDATE participacoes_etapas
            SET status = 'confirmado'
            WHERE id = %s
        ''', (participacao_id,))
        
        conn.commit()
        cursor.close()
        conn.close()
        
        print(f"[DB] ✓ Piloto {piloto_id} confirmou participação em {participacao['etapa_id']}")
        return {'sucesso': True, 'mensagem': 'Participação confirmada com sucesso'}
    except Exception as e:
        print(f"[DB] Erro ao confirmar participação: {e}")
        import traceback
        traceback.print_exc()
        return {'sucesso': False, 'erro': str(e)}

def desistir_participacao_piloto(self, participacao_id: str, piloto_id: str) -> dict:
    """Piloto desiste da participação - admin vai alocar próximo candidato"""
    try:
        conn = self._get_conn()
        cursor = conn.cursor(dictionary=True)
        
        # Verificar se participação existe
        cursor.execute('''
            SELECT etapa_id, equipe_id, piloto_id FROM participacoes_etapas
            WHERE id = %s
        ''', (participacao_id,))
        
        participacao = cursor.fetchone()
        if not participacao:
            cursor.close()
            conn.close()
            return {'sucesso': False, 'erro': 'Participação não encontrada'}
        
        # Verificar se piloto é o correto
        if participacao['piloto_id'] != piloto_id:
            cursor.close()
            conn.close()
            return {'sucesso': False, 'erro': 'Piloto não autorizado'}
        
        etapa_id = participacao['etapa_id']
        equipe_id = participacao['equipe_id']
        
        # Remover piloto de participacoes_etapas
        cursor.execute('''
            UPDATE participacoes_etapas
            SET piloto_id = NULL, status = 'sem_piloto'
            WHERE id = %s
        ''', (participacao_id,))
        
        # Obter próximo candidato (2º, 3º, etc)
        cursor.execute('''
            SELECT id as candidato_id, piloto_id 
            FROM candidatos_piloto_etapa
            WHERE etapa_id = %s AND equipe_id = %s
              AND status IN ('pendente', 'designado')
              AND piloto_id != %s
            ORDER BY data_inscricao ASC
            LIMIT 1
        ''', (etapa_id, equipe_id, piloto_id))
        
        proximo_candidato = cursor.fetchone()
        
        if proximo_candidato:
            # Alocar próximo candidato
            novo_piloto_id = proximo_candidato['piloto_id']
            cursor.execute('''
                UPDATE participacoes_etapas
                SET piloto_id = %s, status = 'inscrita'
                WHERE id = %s
            ''', (novo_piloto_id, participacao_id))
            
            mensagem = f'Próximo candidato alocado'
        else:
            mensagem = 'Nenhum candidato em espera. Admin precisa alocar'
        
        conn.commit()
        cursor.close()
        conn.close()
        
        print(f"[DB] ✓ Piloto {piloto_id} desistiu. {mensagem}")
        return {'sucesso': True, 'mensagem': mensagem, 'proximo_piloto': novo_piloto_id if proximo_candidato else None}
    except Exception as e:
        print(f"[DB] Erro ao processar desistência: {e}")
        import traceback
        traceback.print_exc()
        return {'sucesso': False, 'erro': str(e)}

def alocar_proximo_piloto_candidato(self, etapa_id: str, equipe_id: str) -> dict:
    """Admin aloca próximo piloto candidato para uma equipe"""
    try:
        conn = self._get_conn()
        cursor = conn.cursor(dictionary=True)
        
        # Obter próximo candidato (1º que se candidatou e ainda está disponível)
        cursor.execute('''
            SELECT 
                cpe.id as candidato_id,
                cpe.piloto_id,
                pi.nome as piloto_nome
            FROM candidatos_piloto_etapa cpe
            INNER JOIN pilotos pi ON cpe.piloto_id = pi.id
            WHERE cpe.etapa_id = %s AND cpe.equipe_id = %s
              AND cpe.status IN ('pendente', 'designado')
            ORDER BY cpe.data_inscricao ASC
            LIMIT 1
        ''', (etapa_id, equipe_id))
        
        candidato = cursor.fetchone()
        
        if not candidato:
            cursor.close()
            conn.close()
            return {'sucesso': False, 'erro': 'Nenhum candidato disponível para esta equipe'}
        
        piloto_id = candidato['piloto_id']
        
        # Verificar se piloto já está alocado em outra equipe desta etapa
        cursor.execute('''
            SELECT equipe_id FROM participacoes_etapas
            WHERE etapa_id = %s AND piloto_id = %s AND piloto_id IS NOT NULL
        ''', (etapa_id, piloto_id))
        
        if cursor.fetchone():
            cursor.close()
            conn.close()
            return {'sucesso': False, 'erro': f'Piloto {candidato["piloto_nome"]} já está alocado em outra equipe nesta etapa'}
        
        # Atualizar participacoes_etapas com piloto
        cursor.execute('''
            UPDATE participacoes_etapas
            SET piloto_id = %s, status = 'inscrita'
            WHERE etapa_id = %s AND equipe_id = %s
        ''', (piloto_id, etapa_id, equipe_id))
        
        # Marcar candidato como designado
        cursor.execute('''
            UPDATE candidatos_piloto_etapa
            SET status = 'designado'
            WHERE id = %s
        ''', (candidato['candidato_id'],))
        
        conn.commit()
        cursor.close()
        conn.close()
        
        print(f"[DB] ✓ Piloto {candidato['piloto_nome']} alocado para equipe {equipe_id}")
        return {
            'sucesso': True,
            'piloto_id': piloto_id,
            'piloto_nome': candidato['piloto_nome'],
            'mensagem': f'Piloto {candidato["piloto_nome"]} alocado com sucesso'
        }
    except Exception as e:
        print(f"[DB] Erro ao alocar piloto: {e}")
        import traceback
        traceback.print_exc()
        return {'sucesso': False, 'erro': str(e)}

def obter_pilotos_sem_equipe(self, etapa_id: str) -> dict:
    """Retorna pilotos que se candidataram mas não foram alocados para nenhuma equipe"""
    try:
        conn = self._get_conn()
        cursor = conn.cursor(dictionary=True)
        
        cursor.execute('''
            SELECT 
                cpe.id as candidato_id,
                cpe.piloto_id,
                pi.nome as piloto_nome,
                cpe.data_inscricao,
                COALESCE(e.nome, 'N/A') as equipe_nome,
                COUNT(*) OVER () as total_sem_equipe
            FROM candidatos_piloto_etapa cpe
            INNER JOIN pilotos pi ON cpe.piloto_id = pi.id
            LEFT JOIN equipes e ON cpe.equipe_id = e.id
            WHERE cpe.etapa_id = %s 
              AND cpe.status IN ('pendente', 'designado')
              AND NOT EXISTS (
                SELECT 1 FROM participacoes_etapas pe
                WHERE pe.etapa_id = %s AND pe.piloto_id = cpe.piloto_id
              )
            ORDER BY cpe.data_inscricao ASC
        ''', (etapa_id, etapa_id))
        
        pilotos = cursor.fetchall()
        cursor.close()
        conn.close()
        
        total = pilotos[0]['total_sem_equipe'] if pilotos else 0
        
        return {
            'sucesso': True,
            'pilotos': pilotos or [],
            'total': total
        }
    except Exception as e:
        print(f"[DB] Erro ao obter pilotos sem equipe: {e}")
        import traceback
        traceback.print_exc()
        return {'sucesso': False, 'erro': str(e), 'pilotos': [], 'total': 0}

def alocar_piloto_reserva_para_equipe(self, etapa_id: str, equipe_id: str, piloto_id: str) -> dict:
    """Admin aloca um piloto da fila de reserva para uma equipe que falta piloto"""
    try:
        conn = self._get_conn()
        cursor = conn.cursor(dictionary=True)
        
        # Verificar se piloto existe e não está alocado
        cursor.execute('''
            SELECT nome FROM pilotos WHERE id = %s
        ''', (piloto_id,))
        
        piloto = cursor.fetchone()
        if not piloto:
            cursor.close()
            conn.close()
            return {'sucesso': False, 'erro': 'Piloto não encontrado'}
        
        # Verificar se piloto já está alocado nesta etapa
        cursor.execute('''
            SELECT equipe_id FROM participacoes_etapas
            WHERE etapa_id = %s AND piloto_id = %s AND piloto_id IS NOT NULL
        ''', (etapa_id, piloto_id))
        
        if cursor.fetchone():
            cursor.close()
            conn.close()
            return {'sucesso': False, 'erro': 'Piloto já está alocado em outra equipe nesta etapa'}
        
        # Atualizar participacoes_etapas
        cursor.execute('''
            UPDATE participacoes_etapas
            SET piloto_id = %s, status = 'inscrita'
            WHERE etapa_id = %s AND equipe_id = %s
        ''', (piloto_id, etapa_id, equipe_id))
        
        conn.commit()
        cursor.close()
        conn.close()
        
        print(f"[DB] ✓ Piloto reserva {piloto['nome']} alocado para equipe {equipe_id}")
        return {
            'sucesso': True,
            'mensagem': f'Piloto {piloto["nome"]} alocado com sucesso'
        }
    except Exception as e:
        print(f"[DB] Erro ao alocar piloto reserva: {e}")
        import traceback
        traceback.print_exc()
        return {'sucesso': False, 'erro': str(e)}
