"""
Sistema de persistência de dados usando JSON e SQLite
"""
import json
import sqlite3
import pymysql
from pymysql.cursors import DictCursor
import re  # Regular expression module for parsing MySQL connection strings
import traceback
import base64  # Para codificar/decodificar imagens
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict, Any
from .models import (
    Peca, Carro, Piloto, Equipe, Batalha, Etapa,
    TipoDiferencial, ResultadoBatalha
)


class DatabaseManager:
    """Gerencia a persistência de dados no banco de dados"""

    def __init__(self, db_path: str = "mysql://user:password@localhost:3306/granpix"):
        self.db_path = db_path
        self.is_mysql = True  # Force MySQL usage
        self.init_database()

    def _get_conn(self, use_db=True):
        # Conexão MySQL/MariaDB via PyMySQL (compatível com MariaDB, collation explícita)
        m = re.match(r"mysql://([^:@]+)(?::([^@]*))?@([^:/]+)(?::(\d+))?/([^?]+)", self.db_path)
        if not m:
            raise ValueError("String de conexão MySQL inválida")
        user, password, host, port, db = m.groups()
        password = password or ""
        port = int(port) if port else 3306
        kwargs = dict(
            host=host,
            user=user,
            password=password,
            port=port,
            charset="utf8mb4",
            collation="utf8mb4_unicode_ci",
        )
        if use_db:
            kwargs["database"] = db
        raw = pymysql.connect(**kwargs)
        # Wrapper para compatibilidade com código que usa cursor(dictionary=True) (mysql.connector)
        class _ConnWrapper:
            def __init__(self, conn):
                self._raw = conn
            def __getattr__(self, name):
                return getattr(self._raw, name)
            def cursor(self, dictionary=False, **kw):
                if dictionary:
                    return self._raw.cursor(DictCursor, **kw)
                return self._raw.cursor(**kw)
            def close(self):
                return self._raw.close()
            def commit(self):
                return self._raw.commit()
        return _ConnWrapper(raw)

    def _column_exists(self, table_name: str, column_name: str) -> bool:
        """Verifica se uma coluna existe na tabela"""
        conn = self._get_conn()
        cursor = conn.cursor()
        try:
            if self.is_mysql:
                cursor.execute("""
                    SELECT COUNT(*) 
                    FROM information_schema.COLUMNS 
                    WHERE TABLE_SCHEMA = DATABASE() 
                    AND TABLE_NAME = %s 
                    AND COLUMN_NAME = %s
                """, (table_name, column_name))
                return cursor.fetchone()[0] > 0
            else:
                cursor.execute(f"PRAGMA table_info({table_name})")
                columns = [col[1] for col in cursor.fetchall()]
                return column_name in columns
        finally:
            conn.close()

    def _table_exists(self, table_name: str) -> bool:
        """Verifica se uma tabela existe no banco de dados"""
        conn = self._get_conn()
        cursor = conn.cursor()
        try:
            if self.is_mysql:
                cursor.execute("""
                    SELECT COUNT(*) 
                    FROM information_schema.TABLES 
                    WHERE TABLE_SCHEMA = DATABASE() 
                    AND TABLE_NAME = %s
                """, (table_name,))
                return cursor.fetchone()[0] > 0
            else:
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=%s", (table_name,))
                return cursor.fetchone() is not None
        finally:
            conn.close()

    def init_database(self) -> None:
        """Inicializa as tabelas do banco de dados"""
        m = re.match(r"mysql://([^:@]+)(?::([^@]*))?@([^:/]+)(?::(\d+))?/([^?]+)", self.db_path)
        db_name = m.group(5) if m else "granpix"
        if not re.match(r"^[a-zA-Z0-9_]+$", db_name):
            db_name = "granpix"
        # Conecta sem banco para criar o banco se necessário
        conn = self._get_conn(use_db=False)
        cursor = conn.cursor()
        cursor.execute(
            "CREATE DATABASE IF NOT EXISTS `%s` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
            % db_name.replace("`", "``")
        )
        conn.close()
        # Agora conecta ao banco normalmente
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute("USE `%s`;" % db_name.replace("`", "``"))
        # Desabilitar verificação de foreign keys temporariamente
        cursor.execute("SET FOREIGN_KEY_CHECKS=0")

        # Tabela de Equipes
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS equipes (
                id VARCHAR(64) PRIMARY KEY,
                nome VARCHAR(255) NOT NULL UNIQUE,
                serie VARCHAR(1) DEFAULT 'A',
                doricoins DOUBLE DEFAULT 0.0,
                saldo_pix DOUBLE DEFAULT 0.0,
                data_criacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                senha VARCHAR(255) DEFAULT ''
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        ''')
        
        # Adicionar coluna serie se não existir
        if not self._column_exists('equipes', 'serie'):
            try:
                cursor.execute("ALTER TABLE equipes ADD COLUMN serie VARCHAR(1) DEFAULT 'A'")
                conn.commit()
                print("[DB] Coluna serie adicionada à tabela equipes")
            except Exception as e:
                print(f"[DB] Erro ao adicionar coluna serie: {e}")

        # Tabela de Carros
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS carros (
                id VARCHAR(64) PRIMARY KEY,
                numero_carro INT NOT NULL UNIQUE,
                marca VARCHAR(255) NOT NULL,
                modelo VARCHAR(255) NOT NULL,
                batidas_totais INT DEFAULT 0,
                vitoria INT DEFAULT 0,
                derrotas INT DEFAULT 0,
                empates INT DEFAULT 0,
                equipe_id VARCHAR(64),
                data_criacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                modelo_id VARCHAR(64),
                status VARCHAR(64) DEFAULT 'repouso',
                timestamp_ativo TIMESTAMP NULL,
                timestamp_repouso TIMESTAMP NULL,
                FOREIGN KEY (equipe_id) REFERENCES equipes(id),
                FOREIGN KEY (modelo_id) REFERENCES modelos_carro_loja(id)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        ''')

        # Tabela de Peças
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS pecas (
                id VARCHAR(64) PRIMARY KEY,
                carro_id VARCHAR(64),
                peca_loja_id VARCHAR(64),
                nome VARCHAR(255) NOT NULL,
                tipo VARCHAR(64) NOT NULL,
                durabilidade_maxima DOUBLE NOT NULL,
                durabilidade_atual DOUBLE NOT NULL,
                preco DOUBLE DEFAULT 0.0,
                coeficiente_quebra DOUBLE DEFAULT 1.0,
                instalado BOOLEAN DEFAULT 0,
                data_criacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (carro_id) REFERENCES carros(id) ON DELETE SET NULL,
                FOREIGN KEY (peca_loja_id) REFERENCES pecas_loja(id) ON DELETE SET NULL
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        ''')

        # Tabela de Pilotos
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS pilotos (
                id VARCHAR(64) PRIMARY KEY,
                nome VARCHAR(255) NOT NULL,
                equipe_id VARCHAR(64) NOT NULL,
                vitoria INT DEFAULT 0,
                derrotas INT DEFAULT 0,
                empates INT DEFAULT 0,
                data_criacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (equipe_id) REFERENCES equipes(id)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        ''')

        # Tabela de Batalhas
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS batalhas (
                id VARCHAR(64) PRIMARY KEY,
                piloto_a_id VARCHAR(64) NOT NULL,
                piloto_b_id VARCHAR(64) NOT NULL,
                equipe_a_id VARCHAR(64) NOT NULL,
                equipe_b_id VARCHAR(64) NOT NULL,
                etapa INT NOT NULL,
                data TIMESTAMP NOT NULL,
                resultado VARCHAR(64),
                empates_ate_vencer INT DEFAULT 0,
                doricoins_vencedor DOUBLE DEFAULT 1000.0,
                desgaste_base DOUBLE DEFAULT 15.0,
                FOREIGN KEY (piloto_a_id) REFERENCES pilotos(id),
                FOREIGN KEY (piloto_b_id) REFERENCES pilotos(id),
                FOREIGN KEY (equipe_a_id) REFERENCES equipes(id),
                FOREIGN KEY (equipe_b_id) REFERENCES equipes(id)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        ''')

        # Tabela de Campeonatos
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS campeonatos (
                id VARCHAR(64) PRIMARY KEY,
                nome VARCHAR(255) NOT NULL,
                descricao TEXT DEFAULT '',
                serie VARCHAR(1) NOT NULL,
                numero_etapas INT DEFAULT 5,
                status VARCHAR(20) DEFAULT 'ativo',
                data_criacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                data_atualizacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                UNIQUE KEY unique_nome_serie (nome, serie),
                INDEX idx_serie (serie)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        ''')

        # Tabela de Etapas (atualizada com campeonato_id)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS etapas (
                id VARCHAR(64) PRIMARY KEY,
                campeonato_id VARCHAR(64) NOT NULL,
                numero INT NOT NULL,
                nome VARCHAR(255) NOT NULL,
                descricao TEXT DEFAULT '',
                data_etapa DATE NOT NULL,
                hora_etapa TIME NOT NULL,
                serie VARCHAR(1) NOT NULL DEFAULT '',
                status VARCHAR(20) DEFAULT 'agendada',
                data_criacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                data_atualizacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                FOREIGN KEY (campeonato_id) REFERENCES campeonatos(id) ON DELETE CASCADE,
                INDEX idx_campeonato (campeonato_id),
                INDEX idx_serie (serie)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        ''')

        # Tabela de Participações em Etapas
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS participacoes_etapas (
                id VARCHAR(64) PRIMARY KEY,
                etapa_id VARCHAR(64) NOT NULL,
                equipe_id VARCHAR(64),
                piloto_id VARCHAR(64),
                carro_id VARCHAR(64),
                status VARCHAR(20) DEFAULT 'inscrita',
                tipo_participacao VARCHAR(30) DEFAULT 'equipe_completa',
                data_inscricao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                data_atualizacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                FOREIGN KEY (etapa_id) REFERENCES etapas(id),
                FOREIGN KEY (equipe_id) REFERENCES equipes(id),
                FOREIGN KEY (piloto_id) REFERENCES pilotos(id),
                UNIQUE KEY unique_etapa_equipe (etapa_id, equipe_id),
                INDEX idx_etapa (etapa_id),
                INDEX idx_equipe (equipe_id),
                INDEX idx_piloto (piloto_id)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        ''')

        # Tabela de Vínculo Piloto x Equipe (N:N)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS pilotos_equipes (
                id VARCHAR(64) PRIMARY KEY,
                piloto_id VARCHAR(64) NOT NULL,
                equipe_id VARCHAR(64) NOT NULL,
                codigo_convite VARCHAR(32) NOT NULL UNIQUE,
                status VARCHAR(20) DEFAULT 'ativo',
                data_vinculacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (piloto_id) REFERENCES pilotos(id) ON DELETE CASCADE,
                FOREIGN KEY (equipe_id) REFERENCES equipes(id) ON DELETE CASCADE,
                UNIQUE KEY unique_piloto_equipe (piloto_id, equipe_id),
                INDEX idx_piloto (piloto_id),
                INDEX idx_equipe (equipe_id),
                INDEX idx_codigo (codigo_convite)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        ''')

        # Tabela de Códigos de Convite para Pilotos
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS convites_pilotos (
                id VARCHAR(64) PRIMARY KEY,
                equipe_id VARCHAR(64) NOT NULL,
                codigo VARCHAR(32) NOT NULL UNIQUE,
                data_geracao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                data_expiracao TIMESTAMP NULL,
                usos_restantes INT DEFAULT 10,
                status VARCHAR(20) DEFAULT 'ativo',
                FOREIGN KEY (equipe_id) REFERENCES equipes(id) ON DELETE CASCADE,
                INDEX idx_equipe (equipe_id),
                INDEX idx_codigo (codigo)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        ''')

        # Tabela de Candidatos Pilotos para Equipes em Etapas (Inscrições de Pilotos)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS candidatos_piloto_etapa (
                id VARCHAR(64) PRIMARY KEY,
                etapa_id VARCHAR(64) NOT NULL,
                equipe_id VARCHAR(64) NOT NULL,
                piloto_id VARCHAR(64) NOT NULL,
                status VARCHAR(20) DEFAULT 'pendente',
                data_inscricao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                data_atualizacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                FOREIGN KEY (etapa_id) REFERENCES etapas(id) ON DELETE CASCADE,
                FOREIGN KEY (equipe_id) REFERENCES equipes(id) ON DELETE CASCADE,
                FOREIGN KEY (piloto_id) REFERENCES pilotos(id) ON DELETE CASCADE,
                UNIQUE KEY unique_candidato (etapa_id, equipe_id, piloto_id),
                INDEX idx_etapa (etapa_id),
                INDEX idx_equipe (equipe_id),
                INDEX idx_piloto (piloto_id),
                INDEX idx_status (status)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        ''')

        # Tabela de Pecas da Loja
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS pecas_loja (
                id VARCHAR(64) PRIMARY KEY,
                nome VARCHAR(255) NOT NULL,
                tipo VARCHAR(64) NOT NULL,
                preco DOUBLE NOT NULL,
                descricao TEXT,
                compatibilidade VARCHAR(255) DEFAULT "universal",
                durabilidade DOUBLE DEFAULT 100.0,
                coeficiente_quebra DOUBLE DEFAULT 1.0,
                data_criacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        ''')

        # Tabela de Modelos de Carros da Loja
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS modelos_carro_loja (
                id VARCHAR(64) PRIMARY KEY,
                marca VARCHAR(255) NOT NULL,
                modelo VARCHAR(255) NOT NULL,
                classe VARCHAR(64) NOT NULL,
                preco DOUBLE NOT NULL,
                descricao TEXT,
                motor_id VARCHAR(64),
                cambio_id VARCHAR(64),
                suspensao VARCHAR(32) DEFAULT 'original',
                kit_angulo VARCHAR(32) DEFAULT 'original',
                diferencial VARCHAR(32) DEFAULT 'original',
                data_criacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (motor_id) REFERENCES pecas_loja(id),
                FOREIGN KEY (cambio_id) REFERENCES pecas_loja(id)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        ''')

        # Tabela de Solicitações de Carros
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS solicitacoes_carros (
                id VARCHAR(64) PRIMARY KEY,
                equipe_id VARCHAR(64) NOT NULL,
                carro_id VARCHAR(64),
                carro_anterior_id VARCHAR(64),
                tipo_carro VARCHAR(255) NOT NULL,
                tipo_solicitacao VARCHAR(64) DEFAULT 'ativacao',
                status VARCHAR(64) DEFAULT 'pendente',
                data_solicitacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                data_atualizacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                FOREIGN KEY (equipe_id) REFERENCES equipes(id),
                FOREIGN KEY (carro_id) REFERENCES carros(id),
                FOREIGN KEY (carro_anterior_id) REFERENCES carros(id),
                INDEX idx_equipe (equipe_id),
                INDEX idx_status (status)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        ''')

        # Tabela de Solicitações de Peças
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS solicitacoes_pecas (
                id VARCHAR(64) PRIMARY KEY,
                equipe_id VARCHAR(64) NOT NULL,
                peca_id VARCHAR(64),
                carro_id VARCHAR(64),
                tipo_peca VARCHAR(255),
                quantidade INT DEFAULT 1,
                status VARCHAR(64) DEFAULT 'pendente',
                data_solicitacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                data_atualizacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                FOREIGN KEY (equipe_id) REFERENCES equipes(id),
                FOREIGN KEY (peca_id) REFERENCES pecas_loja(id),
                FOREIGN KEY (carro_id) REFERENCES carros(id)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        ''')

        # Tabela de Configurações (para taxas de comissão)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS configuracoes (
                id VARCHAR(64) PRIMARY KEY,
                chave VARCHAR(255) NOT NULL UNIQUE,
                valor VARCHAR(255) NOT NULL,
                descricao TEXT,
                data_criacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                data_atualizacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        ''')

        # Tabela de Comissões (pagamentos ao mecanico)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS comissoes (
                id VARCHAR(64) PRIMARY KEY,
                tipo VARCHAR(64) NOT NULL COMMENT 'compra_carro, compra_peca, instalar_peca',
                valor_comissao DOUBLE NOT NULL,
                equipe_id VARCHAR(64),
                equipe_nome VARCHAR(255),
                descricao VARCHAR(255),
                data_transacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                INDEX idx_tipo (tipo),
                INDEX idx_equipe (equipe_id),
                INDEX idx_data (data_transacao)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        ''')

        # Tabela de transações PIX
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS transacoes_pix (
                id VARCHAR(64) PRIMARY KEY,
                mercado_pago_id VARCHAR(255) UNIQUE,
                equipe_id VARCHAR(64) NOT NULL,
                equipe_nome VARCHAR(255),
                tipo_item VARCHAR(64) COMMENT 'carro ou peca',
                item_id VARCHAR(64),
                item_nome VARCHAR(255),
                valor_item DOUBLE NOT NULL,
                valor_taxa DOUBLE NOT NULL DEFAULT 0,
                valor_total DOUBLE NOT NULL,
                status VARCHAR(64) DEFAULT 'pendente' COMMENT 'pendente, aprovado, recusado, cancelado',
                qr_code TEXT,
                qr_code_url VARCHAR(500),
                data_criacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                data_confirmacao TIMESTAMP NULL,
                descricao VARCHAR(500),
                INDEX idx_equipe (equipe_id),
                INDEX idx_status (status),
                INDEX idx_mp_id (mercado_pago_id),
                INDEX idx_data (data_criacao)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        ''')

        # Add a senha column to the equipes table if it does not exist
        if not self._column_exists('equipes', 'senha'):
            cursor.execute('''
                ALTER TABLE equipes ADD COLUMN senha VARCHAR(255) DEFAULT ''
            ''')

        # Add a serie column to the equipes table if it does not exist
        if not self._column_exists('equipes', 'serie'):
            cursor.execute('''
                ALTER TABLE equipes ADD COLUMN serie VARCHAR(1) DEFAULT ''
            ''')

        # Adicionar coluna peca_loja_id à tabela pecas se não existir
        if not self._column_exists('pecas', 'peca_loja_id'):
            cursor.execute('''
                ALTER TABLE pecas ADD COLUMN peca_loja_id VARCHAR(64) AFTER carro_id
            ''')

        # Adicionar coluna peca_id à tabela solicitacoes_pecas se não existir
        if not self._column_exists('solicitacoes_pecas', 'peca_id'):
            cursor.execute('''
                ALTER TABLE solicitacoes_pecas ADD COLUMN peca_id VARCHAR(64) AFTER equipe_id
            ''')

        # Adicionar coluna carro_id à tabela solicitacoes_pecas se não existir
        if not self._column_exists('solicitacoes_pecas', 'carro_id'):
            cursor.execute('''
                ALTER TABLE solicitacoes_pecas ADD COLUMN carro_id VARCHAR(64) AFTER peca_id
            ''')

        # Adicionar coluna instalado à tabela pecas se não existir
        if not self._column_exists('pecas', 'instalado'):
            cursor.execute('''
                ALTER TABLE pecas ADD COLUMN instalado BOOLEAN DEFAULT 0
            ''')

        # Adicionar coluna data_criacao à tabela pecas se não existir
        if not self._column_exists('pecas', 'data_criacao'):
            cursor.execute('''
                ALTER TABLE pecas ADD COLUMN data_criacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            ''')

        # Adicionar coluna suspensao_id à tabela modelos_carro_loja se não existir
        if not self._column_exists('modelos_carro_loja', 'suspensao_id'):
            cursor.execute('''
                ALTER TABLE modelos_carro_loja ADD COLUMN suspensao_id VARCHAR(64) AFTER cambio_id
            ''')

        # Adicionar coluna kit_angulo_id à tabela modelos_carro_loja se não existir
        if not self._column_exists('modelos_carro_loja', 'kit_angulo_id'):
            cursor.execute('''
                ALTER TABLE modelos_carro_loja ADD COLUMN kit_angulo_id VARCHAR(64) AFTER suspensao_id
            ''')

        # Adicionar coluna diferencial_id à tabela modelos_carro_loja se não existir
        if not self._column_exists('modelos_carro_loja', 'diferencial_id'):
            cursor.execute('''
                ALTER TABLE modelos_carro_loja ADD COLUMN diferencial_id VARCHAR(64) AFTER kit_angulo_id
            ''')

        # Adicionar coluna imagem à tabela pecas_loja se não existir
        if not self._column_exists('pecas_loja', 'imagem'):
            cursor.execute('''
                ALTER TABLE pecas_loja ADD COLUMN imagem LONGTEXT AFTER coeficiente_quebra
            ''')
        else:
            # Se a coluna já existe e é LONGBLOB, converter para LONGTEXT
            cursor.execute("DESCRIBE pecas_loja")
            colunas = {row[0]: row[1] for row in cursor.fetchall()}
            if 'imagem' in colunas and 'LONGBLOB' in colunas['imagem'].upper():
                print("[DB INIT] Convertendo coluna pecas_loja.imagem de LONGBLOB para LONGTEXT...")
                cursor.execute("ALTER TABLE pecas_loja MODIFY COLUMN imagem LONGTEXT")

        # Adicionar coluna pix_id à tabela pecas se não existir
        if not self._column_exists('pecas', 'pix_id'):
            cursor.execute('''
                ALTER TABLE pecas ADD COLUMN pix_id VARCHAR(64) NULL AFTER instalado
            ''')
            print("[DB INIT] ✅ Coluna pix_id adicionada à tabela pecas")

        # Adicionar coluna equipe_id à tabela pecas se não existir
        if not self._column_exists('pecas', 'equipe_id'):
            cursor.execute('''
                ALTER TABLE pecas ADD COLUMN equipe_id VARCHAR(64) AFTER pix_id
            ''')
            print("[DB INIT] ✅ Coluna equipe_id adicionada à tabela pecas")

        # Adicionar coluna imagem à tabela modelos_carro_loja se não existir
        if not self._column_exists('modelos_carro_loja', 'imagem'):
            cursor.execute('''
                ALTER TABLE modelos_carro_loja ADD COLUMN imagem LONGTEXT AFTER data_criacao
            ''')
        else:
            # Se a coluna já existe e é LONGBLOB, converter para LONGTEXT
            cursor.execute("DESCRIBE modelos_carro_loja")
            colunas = {row[0]: row[1] for row in cursor.fetchall()}
            if 'imagem' in colunas and 'LONGBLOB' in colunas['imagem'].upper():
                print("[DB INIT] Convertendo coluna imagem de LONGBLOB para LONGTEXT...")
                cursor.execute("ALTER TABLE modelos_carro_loja MODIFY COLUMN imagem LONGTEXT")

        # Tabela de Variações de Carros (para separar modelo de variações com diferentes peças)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS variacoes_carros (
                id VARCHAR(64) PRIMARY KEY,
                modelo_carro_loja_id VARCHAR(64) NOT NULL,
                motor_id VARCHAR(64),
                cambio_id VARCHAR(64),
                suspensao_id VARCHAR(64),
                kit_angulo_id VARCHAR(64),
                diferencial_id VARCHAR(64),
                data_criacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (modelo_carro_loja_id) REFERENCES modelos_carro_loja(id) ON DELETE CASCADE,
                FOREIGN KEY (motor_id) REFERENCES pecas_loja(id) ON DELETE SET NULL,
                FOREIGN KEY (cambio_id) REFERENCES pecas_loja(id) ON DELETE SET NULL,
                FOREIGN KEY (suspensao_id) REFERENCES pecas_loja(id) ON DELETE SET NULL,
                FOREIGN KEY (kit_angulo_id) REFERENCES pecas_loja(id) ON DELETE SET NULL,
                FOREIGN KEY (diferencial_id) REFERENCES pecas_loja(id) ON DELETE SET NULL
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        ''')

        # Tabela de Pontuações por Campeonato
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS pontuacoes_campeonato (
                id VARCHAR(64) PRIMARY KEY,
                campeonato_id VARCHAR(64) NOT NULL,
                equipe_id VARCHAR(64) NOT NULL,
                pontos INT DEFAULT 0,
                colocacao INT DEFAULT NULL,
                data_criacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                data_atualizacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                FOREIGN KEY (campeonato_id) REFERENCES campeonatos(id) ON DELETE CASCADE,
                FOREIGN KEY (equipe_id) REFERENCES equipes(id) ON DELETE CASCADE,
                UNIQUE KEY unique_campeonato_equipe (campeonato_id, equipe_id),
                INDEX idx_campeonato (campeonato_id),
                INDEX idx_equipe (equipe_id)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        ''')
        
        # Garantir que a coluna colocacao permite NULL
        if self.is_mysql and self._table_exists('pontuacoes_campeonato'):
            try:
                cursor.execute("ALTER TABLE pontuacoes_campeonato MODIFY COLUMN colocacao INT DEFAULT NULL")
                print("[DB] Coluna colocacao de pontuacoes_campeonato agora permite NULL")
            except Exception as e:
                # Coluna já está correta ou não precisa de ajuste
                pass
        
        # Reabilitar verificação de foreign keys
        cursor.execute("SET FOREIGN_KEY_CHECKS=1")

        conn.commit()
        conn.close()

        # Executar migração para remover colunas obsoletas
        self._remover_colunas_obsoletas()
        # Garantir que equipes tem coluna carro_id (para vincular carro ativo)
        self._ensure_equipes_carro_id()
        # Executar migração para adicionar peças separadas aos carros
        # self._migrar_pecas_separadas_carros()  # DESABILITADO: não queremos essas colunas
        # Executar migração para remover coluna pecas_instaladas
        self._remover_coluna_pecas_instaladas()
        # Executar migração para remover coluna novo_carro_id
        self._remover_coluna_novo_carro_id()
        # Executar migração para adicionar status aos carros
        self._migrar_status_carros()
        # Executar migração para adicionar equipe_id aos carros
        self._migrar_equipe_id_carros()
        # Executar migração para adicionar modelo_id aos carros
        self._migrar_modelo_id_carros()
        # Executar migração para adicionar coeficiente_quebra se necessário
        self._migrar_coeficiente_quebra()
        # Executar migração para adicionar apelido aos carros
        self._migrar_apelido_carro()
        # Executar migração para permitir NULL em carro_id (para peças no armazém)
        self._migrar_carro_id_nullable()
        # Executar migração para adicionar equipe_id às peças
        self._migrar_equipe_id_pecas()
        # Migração para converter compatibilidade para JSON
        self._migrar_compatibilidade_json()
        # Migração para separar variações de carros
        self._migrar_variacoes_carros()
        # Migração para adicionar coluna variacao_carro_id
        self._adicionar_coluna_variacao_carros()
        # Atualizar coeficientes da loja
        self._atualizar_coeficientes_loja()
        # Migração para adicionar coluna valor em variacoes_carros
        self._adicionar_coluna_valor_variacoes()
        # Migração para remover IDs de peças da tabela carros
        self._migrar_remover_coluna_ids_pecas_carros()
        # Migração para adicionar novos campos às etapas
        self._migrar_etapas_temporada()
        # Migração para adicionar ordem de qualificação
        self._migrar_ordem_qualificacao()

    def _migrar_etapas_temporada(self) -> None:
        """Migração: adiciona campos de temporada às etapas"""
        conn = self._get_conn()
        cursor = conn.cursor()
        try:
            # Adicionar campeonato_id
            if not self._column_exists('etapas', 'campeonato_id'):
                cursor.execute('ALTER TABLE etapas ADD COLUMN campeonato_id VARCHAR(64) AFTER id')
                print("[DB] Adicionando coluna campeonato_id às etapas...")
            
            # Adicionar data_etapa
            if not self._column_exists('etapas', 'data_etapa'):
                cursor.execute('ALTER TABLE etapas ADD COLUMN data_etapa DATE DEFAULT CURDATE()')
                print("[DB] Adicionando coluna data_etapa às etapas...")
            
            # Adicionar hora_etapa
            if not self._column_exists('etapas', 'hora_etapa'):
                cursor.execute('ALTER TABLE etapas ADD COLUMN hora_etapa TIME DEFAULT "10:00:00"')
                print("[DB] Adicionando coluna hora_etapa às etapas...")
            
            # Adicionar serie
            if not self._column_exists('etapas', 'serie'):
                cursor.execute('ALTER TABLE etapas ADD COLUMN serie VARCHAR(1) DEFAULT ""')
                print("[DB] Adicionando coluna serie às etapas...")
            
            # Adicionar status
            if not self._column_exists('etapas', 'status'):
                cursor.execute('ALTER TABLE etapas ADD COLUMN status VARCHAR(20) DEFAULT "agendada"')
                print("[DB] Adicionando coluna status às etapas...")
            
            # Adicionar descricao
            if not self._column_exists('etapas', 'descricao'):
                cursor.execute('ALTER TABLE etapas ADD COLUMN descricao TEXT DEFAULT ""')
                print("[DB] Adicionando coluna descricao às etapas...")
            
            conn.commit()
        except Exception as e:
            conn.rollback()
            print(f"[DB] Erro na migração de etapas: {e}")
        finally:
            cursor.close()
            conn.close()

    def _migrar_ordem_qualificacao(self) -> None:
        """Migração: adiciona campo de ordem de qualificação às participações"""
        conn = self._get_conn()
        cursor = conn.cursor()
        try:
            # Adicionar ordem_qualificacao
            if not self._column_exists('participacoes_etapas', 'ordem_qualificacao'):
                cursor.execute('ALTER TABLE participacoes_etapas ADD COLUMN ordem_qualificacao INT DEFAULT NULL')
                print("[DB] Adicionando coluna ordem_qualificacao às participacoes_etapas...")
            
            conn.commit()
        except Exception as e:
            conn.rollback()
            print(f"[DB] Erro na migração de ordem_qualificacao: {e}")
        finally:
            cursor.close()
            conn.close()

    def _remover_colunas_obsoletas(self) -> None:
        """Migração: remove colunas obsoletas da tabela modelos_carro_loja"""
        try:
            conn = self._get_conn()
            cursor = conn.cursor()

            # Remover coluna suspensao se existir (obsoleta, substituída por suspensao_id)
            if self._column_exists('modelos_carro_loja', 'suspensao'):
                print("[DB] Migrando: removendo coluna suspensao (obsoleta)...")
                cursor.execute('ALTER TABLE modelos_carro_loja DROP COLUMN suspensao')
                print("[DB] Coluna suspensao removida!")

            # Remover coluna kit_angulo se existir (obsoleta, substituída por kit_angulo_id)
            if self._column_exists('modelos_carro_loja', 'kit_angulo'):
                print("[DB] Migrando: removendo coluna kit_angulo (obsoleta)...")
                cursor.execute('ALTER TABLE modelos_carro_loja DROP COLUMN kit_angulo')
                print("[DB] Coluna kit_angulo removida!")

            # Remover coluna diferencial se existir (obsoleta, substituída por diferencial_id)
            if self._column_exists('modelos_carro_loja', 'diferencial'):
                print("[DB] Migrando: removendo coluna diferencial (obsoleta)...")
                cursor.execute('ALTER TABLE modelos_carro_loja DROP COLUMN diferencial')
                print("[DB] Coluna diferencial removida!")

            conn.commit()
            conn.close()
        except Exception as e:
            print(f"[DB] Erro ao remover colunas obsoletas: {e}")

    def _ensure_equipes_carro_id(self) -> None:
        """Garante que a tabela equipes tem a coluna carro_id (só adiciona se não existir)."""
        try:
            if not self._column_exists('equipes', 'carro_id'):
                conn = self._get_conn()
                cursor = conn.cursor()
                print("[DB] Adicionando coluna carro_id à tabela equipes...")
                cursor.execute('ALTER TABLE equipes ADD COLUMN carro_id VARCHAR(64) NULL')
                conn.commit()
                conn.close()
                print("[DB] Coluna equipes.carro_id criada.")
        except Exception as e:
            print(f"[DB] Aviso ao garantir equipes.carro_id: {e}")

    def _migrar_equipes(self) -> None:
        """Migração: adiciona carro_id às equipes se a coluna não existir"""
        try:
            conn = self._get_conn()
            cursor = conn.cursor()

            # Verificar se a coluna carro_id existe
            if not self._column_exists('equipes', 'carro_id'):
                print("[DB] Migrando: adicionando coluna carro_id às equipes...")
                cursor.execute('ALTER TABLE equipes ADD COLUMN carro_id TEXT')
                conn.commit()
                print("[DB] Migracao concluida!")
            else:
                # A coluna existe, mas talvez as equipes não tenham carro_id
                # Tentar preencher carro_id para equipes que não têm
                cursor.execute('SELECT COUNT(*) FROM equipes WHERE carro_id IS NULL')
                count = cursor.fetchone()[0]

                if count > 0:
                    print(f"[DB] {count} equipes sem carro associado. Corrigindo...")
                    # Para cada equipe sem carro, criar um novo carro
                    cursor.execute('SELECT id FROM equipes WHERE carro_id IS NULL')
                    equipes_sem_carro = cursor.fetchall()

                    for eq_id, in equipes_sem_carro:
                        # Criar um novo carro para esta equipe
                        import uuid
                        carro_id = str(uuid.uuid4())

                        # Obter numero_carro disponível
                        cursor.execute('SELECT MAX(numero_carro) FROM carros')
                        max_num = cursor.fetchone()[0]
                        numero_carro = (max_num or 0) + 1

                        # Inserir novo carro
                        cursor.execute('''
                            INSERT INTO carros (id, numero_carro, marca, modelo)
                            VALUES (%s, %s, %s, %s)
                        ''', (carro_id, numero_carro, 'Generico', 'Padrao'))

                        # Criar pecas padrão para o carro
                        pecas = [
                            (str(uuid.uuid4()), 'motor', 'Motor Padrao', 100.0, 100.0, 500.0),
                            (str(uuid.uuid4()), 'cambio', 'Cambio Padrao', 100.0, 100.0, 300.0),
                            (str(uuid.uuid4()), 'kit_angulo', 'Kit Angulo Padrao', 100.0, 100.0, 200.0),
                            (str(uuid.uuid4()), 'suspensao', 'Suspensao Padrao', 100.0, 100.0, 250.0),
                        ]

                        for peca_id, tipo, nome, dur_max, dur_atual, preco in pecas:
                            cursor.execute('''
                                INSERT INTO pecas (id, carro_id, nome, tipo, durabilidade_maxima, durabilidade_atual, preco)
                                VALUES (%s, %s, %s, %s, %s, %s, %s)
                            ''', (peca_id, carro_id, nome, tipo, dur_max, dur_atual, preco))

                        # Associar carro à equipe
                        cursor.execute('UPDATE equipes SET carro_id = %s WHERE id = %s', (carro_id, eq_id))

                    conn.commit()
                    print("[DB] Correcao concluida!")
                conn.close()
        except Exception as e:
            print(f"[DB] Erro na migracao: {e}")

    def _migrar_pecas_separadas_carros(self) -> None:
        """Migração: adiciona colunas de peças separadas aos carros"""
        try:
            conn = self._get_conn()
            cursor = conn.cursor()

            # Verificar e adicionar colunas de peças se não existirem
            columns_to_add = [
                ('motor_id', 'VARCHAR(64)'),
                ('cambio_id', 'VARCHAR(64)'),
                ('suspensao_id', 'VARCHAR(64)'),
                ('kit_angulo_id', 'VARCHAR(64)'),
                ('diferencial_id', 'VARCHAR(64)')
            ]

            for col_name, col_type in columns_to_add:
                if not self._column_exists('carros', col_name):
                    print(f"[DB] Migrando: adicionando coluna {col_name} aos carros...")
                    cursor.execute(f'ALTER TABLE carros ADD COLUMN {col_name} {col_type}')
                    conn.commit()
                    print(f"[DB] Coluna {col_name} adicionada!")

            conn.close()
        except Exception as e:
            print(f"[DB] Erro na migração de peças separadas: {e}")

    def _remover_coluna_pecas_instaladas(self) -> None:
        """Migração: remove coluna pecas_instaladas dos carros (agora usando colunas separadas)"""
        try:
            conn = self._get_conn()
            cursor = conn.cursor()

            if self._column_exists('carros', 'pecas_instaladas'):
                print("[DB] Migrando: removendo coluna pecas_instaladas dos carros...")
                cursor.execute('ALTER TABLE carros DROP COLUMN pecas_instaladas')
                conn.commit()
                print("[DB] Coluna pecas_instaladas removida com sucesso!")
            conn.close()
        except Exception as e:
            print(f"[DB] Erro na remoção de pecas_instaladas: {e}")

    def _remover_coluna_novo_carro_id(self) -> None:
        """Migração: remove coluna novo_carro_id de solicitacoes_carros (obsoleta)"""
        try:
            conn = self._get_conn()
            cursor = conn.cursor()

            if self._column_exists('solicitacoes_carros', 'novo_carro_id'):
                print("[DB] Migrando: removendo coluna novo_carro_id de solicitacoes_carros...")
                cursor.execute('ALTER TABLE solicitacoes_carros DROP COLUMN novo_carro_id')
                conn.commit()
                print("[DB] Coluna novo_carro_id removida com sucesso!")
            conn.close()
        except Exception as e:
            print(f"[DB] Erro na remoção de novo_carro_id: {e}")

    def _migrar_status_carros(self) -> None:
        """Migração: adiciona colunas status e timestamps aos carros"""
        try:
            conn = self._get_conn()
            cursor = conn.cursor()

            if not self._column_exists('carros', 'status'):
                print("[DB] Migrando: adicionando coluna status aos carros...")
                cursor.execute('ALTER TABLE carros ADD COLUMN status TEXT DEFAULT "ativo"')
                conn.commit()
                print("[DB] Migracao concluida!")

            if not self._column_exists('carros', 'timestamp_ativo'):
                print("[DB] Migrando: adicionando coluna timestamp_ativo aos carros...")
                cursor.execute('ALTER TABLE carros ADD COLUMN timestamp_ativo TEXT DEFAULT ""')
                conn.commit()

            if not self._column_exists('carros', 'timestamp_repouso'):
                print("[DB] Migrando: adicionando coluna timestamp_repouso aos carros...")
                cursor.execute('ALTER TABLE carros ADD COLUMN timestamp_repouso TEXT DEFAULT ""')
                conn.commit()
            conn.close()
        except Exception as e:
            print(f"[DB] Erro na migracao de status: {e}")

    def _migrar_equipe_id_carros(self) -> None:
        """Migração: adiciona coluna equipe_id aos carros"""
        try:
            conn = self._get_conn()
            cursor = conn.cursor()

            if not self._column_exists('carros', 'equipe_id'):
                print("[DB] Migrando: adicionando coluna equipe_id aos carros...")
                cursor.execute('ALTER TABLE carros ADD COLUMN equipe_id TEXT DEFAULT ""')
                conn.commit()
                print("[DB] Migracao concluida!")
            conn.close()
        except Exception as e:
            print(f"[DB] Erro na migracao de equipe_id: {e}")

    def _migrar_modelo_id_carros(self) -> None:
        """Migração: adiciona coluna modelo_id aos carros"""
        try:
            conn = self._get_conn()
            cursor = conn.cursor()

            if not self._column_exists('carros', 'modelo_id'):
                print("[DB] Migrando: adicionando coluna modelo_id aos carros...")
                cursor.execute('ALTER TABLE carros ADD COLUMN modelo_id VARCHAR(64) DEFAULT NULL')
                conn.commit()
                print("[DB] Migracao concluida!")
            conn.close()
        except Exception as e:
            print(f"[DB] Erro na migracao de modelo_id: {e}")

    def _migrar_coeficiente_quebra(self) -> None:
        """Migração: adiciona coluna coeficiente_quebra às peças se não existir"""
        try:
            conn = self._get_conn()
            cursor = conn.cursor()

            # Verificar se a coluna coeficiente_quebra existe
            if not self._column_exists('pecas', 'coeficiente_quebra'):
                print("[DB] Migrando: adicionando coluna coeficiente_quebra às peças...")
                cursor.execute('ALTER TABLE pecas ADD COLUMN coeficiente_quebra REAL DEFAULT 1.0')
                conn.commit()
                print("[DB] Migracao concluida!")
            conn.close()
        except Exception as e:
            print(f"[DB] Erro na migracao de coeficiente_quebra: {e}")

    def _migrar_apelido_carro(self) -> None:
        """Migração: adiciona coluna apelido aos carros se não existir"""
        try:
            conn = self._get_conn()
            cursor = conn.cursor()

            # Verificar se a coluna apelido existe
            if not self._column_exists('carros', 'apelido'):
                print("[DB] Migrando: adicionando coluna apelido aos carros...")
                cursor.execute('ALTER TABLE carros ADD COLUMN apelido VARCHAR(255) DEFAULT NULL')
                conn.commit()
                print("[DB] Migracao concluida!")
            conn.close()
        except Exception as e:
            print(f"[DB] Erro na migracao de apelido: {e}")

    def _migrar_carro_id_nullable(self) -> None:
        """Migração: permite NULL em carro_id (para peças no armazém)"""
        try:
            conn = self._get_conn()
            cursor = conn.cursor()

            print("[DB] Migrando: alterando carro_id para permitir NULL...")
            
            # Desabilitar foreign key checks temporariamente
            cursor.execute("SET FOREIGN_KEY_CHECKS=0")
            
            # Modificar a coluna para permitir NULL
            cursor.execute('''
                ALTER TABLE pecas 
                MODIFY COLUMN carro_id VARCHAR(64) NULL
            ''')
            
            # Reabilitar foreign key checks
            cursor.execute("SET FOREIGN_KEY_CHECKS=1")
            
            conn.commit()
            conn.close()
            print("[DB] Coluna carro_id agora permite NULL!")
        except Exception as e:
            print(f"[DB] Erro na migracao de carro_id nullable: {e}")

    def _migrar_equipe_id_pecas(self) -> None:
        """Migração: adiciona equipe_id à tabela pecas para rastrear proprietário"""
        try:
            conn = self._get_conn()
            cursor = conn.cursor()

            # Verificar se a coluna equipe_id já existe
            if not self._column_exists('pecas', 'equipe_id'):
                print("[DB] Migrando: adicionando coluna equipe_id à tabela pecas...")
                
                cursor.execute('''
                    ALTER TABLE pecas 
                    ADD COLUMN equipe_id VARCHAR(64) NULL AFTER carro_id
                ''')
                
                conn.commit()
                print("[DB] Coluna equipe_id adicionada à tabela pecas!")
            else:
                print("[DB] Coluna equipe_id já existe na tabela pecas")
            
            conn.close()
        except Exception as e:
            print(f"[DB] Erro ao adicionar equipe_id em pecas: {e}")

    def _migrar_compatibilidade_json(self) -> None:
        """Migração: converte compatibilidade de string para JSON na tabela pecas_loja"""
        try:
            conn = self._get_conn()
            cursor = conn.cursor()

            # Verificar se a coluna já é TEXT (indica migração completa)
            cursor.execute("""
                SELECT COLUMN_TYPE 
                FROM information_schema.COLUMNS 
                WHERE TABLE_SCHEMA = DATABASE() 
                AND TABLE_NAME = 'pecas_loja' 
                AND COLUMN_NAME = 'compatibilidade'
            """)
            result = cursor.fetchone()
            
            if result and 'text' not in result[0].lower():
                print("[DB] Migrando: convertendo compatibilidade para JSON...")
                
                # Primeiro, ler todas as peças atuais
                cursor.execute('SELECT id, compatibilidade FROM pecas_loja')
                pecas = cursor.fetchall()
                
                # Alterar a coluna para TEXT
                cursor.execute('''
                    ALTER TABLE pecas_loja 
                    MODIFY COLUMN compatibilidade TEXT DEFAULT '{"compatibilidades": ["universal"]}'
                ''')
                conn.commit()
                
                # Converter dados existentes para JSON
                for peca_id, compatibilidade in pecas:
                    if compatibilidade and compatibilidade.lower() != 'universal':
                        # Separar por vírgula ou pipe se existirem
                        items = []
                        for item in compatibilidade.split(','):
                            item = item.strip()
                            if item:
                                items.append(item)
                        if not items:
                            items = ['universal']
                        json_data = json.dumps({"compatibilidades": items})
                    else:
                        json_data = json.dumps({"compatibilidades": ["universal"]})
                    
                    cursor.execute(
                        'UPDATE pecas_loja SET compatibilidade = %s WHERE id = %s',
                        (json_data, peca_id)
                    )
                
                conn.commit()
                print("[DB] Compatibilidade convertida para JSON!")
            else:
                print("[DB] Compatibilidade já está em formato JSON")
            
            conn.close()
        except Exception as e:
            print(f"[DB] Erro ao migrar compatibilidade para JSON: {e}")
            traceback.print_exc()

    def _migrar_variacoes_carros(self) -> None:
        """Migração: move peças de modelos_carro_loja para tabela variacoes_carros"""
        try:
            conn = self._get_conn()
            cursor = conn.cursor()
            
            # Verificar se já foi migrado (se variacoes_carros tem dados)
            cursor.execute("SELECT COUNT(*) FROM variacoes_carros")
            if cursor.fetchone()[0] > 0:
                print("[DB] Variações de carros já foram migradas")
                conn.close()
                return
            
            print("[DB] Migrando: movendo peças de modelos_carro_loja para variacoes_carros...")
            
            # Ler todos os modelos de carros com suas peças
            cursor.execute('''
                SELECT id, motor_id, cambio_id, suspensao_id, kit_angulo_id, diferencial_id
                FROM modelos_carro_loja
            ''')
            modelos = cursor.fetchall()
            
            import uuid
            
            for modelo_id, motor_id, cambio_id, suspensao_id, kit_angulo_id, diferencial_id in modelos:
                # Criar uma variação para este modelo
                variacao_id = str(uuid.uuid4())
                
                cursor.execute('''
                    INSERT INTO variacoes_carros 
                    (id, modelo_carro_loja_id, motor_id, cambio_id, suspensao_id, kit_angulo_id, diferencial_id)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                ''', (variacao_id, modelo_id, motor_id, cambio_id, suspensao_id, kit_angulo_id, diferencial_id))
            
            conn.commit()
            print(f"[DB] {len(modelos)} variações criadas a partir de modelos existentes")
            
            conn.close()
        except Exception as e:
            print(f"[DB] Erro ao migrar variacoes_carros: {e}")
            traceback.print_exc()

    def _adicionar_coluna_variacao_carros(self) -> None:
        """Migração: adiciona coluna variacao_carro_id na tabela carros"""
        try:
            if not self._column_exists('carros', 'variacao_carro_id'):
                print("[DB] Migrando: adicionando coluna variacao_carro_id em carros...")
                conn = self._get_conn()
                cursor = conn.cursor()
                
                cursor.execute('''
                    ALTER TABLE carros ADD COLUMN variacao_carro_id VARCHAR(64),
                    ADD FOREIGN KEY (variacao_carro_id) REFERENCES variacoes_carros(id) ON DELETE CASCADE
                ''')
                
                conn.commit()
                conn.close()
                print("[DB] Coluna variacao_carro_id adicionada com sucesso")
            else:
                print("[DB] Coluna variacao_carro_id já existe")
        except Exception as e:
            print(f"[DB] Erro ao adicionar coluna variacao_carro_id: {e}")
            traceback.print_exc()

    def _atualizar_coeficientes_loja(self) -> None:
        """Atualiza os coeficientes das peças da loja no banco de dados"""
        try:
            from .loja_pecas import LojaPecas

            conn = self._get_conn()
            cursor = conn.cursor()

            # Verificar se a coluna coeficiente_quebra existe na tabela pecas_loja
            if not self._column_exists('pecas_loja', 'coeficiente_quebra'):
                print("[DB] Migrando: adicionando coluna coeficiente_quebra à tabela pecas_loja...")
                cursor.execute('ALTER TABLE pecas_loja ADD COLUMN coeficiente_quebra REAL DEFAULT 1.0')
                conn.commit()
                print("[DB] Migracao concluida!")

            # Atualizar os coeficientes das peças
            loja = LojaPecas()

            for peca in loja.pecas:
                cursor.execute('''
                    UPDATE pecas_loja SET coeficiente_quebra = ?
                    WHERE id = ?
                ''', (peca.coeficiente_quebra, peca.id))

            conn.commit()
            conn.close()
            print("[DB] Coeficientes da loja atualizados!")
        except Exception as e:
            print(f"[DB] Erro ao atualizar coeficientes: {e}")

    def _adicionar_coluna_valor_variacoes(self) -> None:
        """Migração: adiciona coluna valor na tabela variacoes_carros"""
        try:
            if not self._column_exists('variacoes_carros', 'valor'):
                print("[DB] Migrando: adicionando coluna valor em variacoes_carros...")
                conn = self._get_conn()
                cursor = conn.cursor()
                
                cursor.execute('''
                    ALTER TABLE variacoes_carros ADD COLUMN valor DECIMAL(10, 2) DEFAULT 0.00
                ''')
                
                conn.commit()
                conn.close()
                print("[DB] Coluna valor adicionada com sucesso")
            else:
                print("[DB] Coluna valor já existe em variacoes_carros")
        except Exception as e:
            print(f"[DB] Erro ao adicionar coluna valor: {e}")
            traceback.print_exc()

    def salvar_equipe(self, equipe: Equipe) -> bool:
        """Salva uma equipe no banco de dados"""
        try:
            print(f"[DB] Salvando equipe {equipe.nome}...")
            # Salvar o carro primeiro (com todas as peças e seus desgastes)
            if equipe.carro:
                print(f"[DB] Salvando carro ativo: {equipe.carro.marca} {equipe.carro.modelo}")
                self.salvar_carro(equipe.carro, equipe.id)

            # Salvar todos os carros em repouso
            if hasattr(equipe, 'carros') and equipe.carros:
                print(f"[DB] Salvando {len(equipe.carros)} carros...")
                for idx, carro in enumerate(equipe.carros):
                    print(f"[DB]   Carro {idx+1}: {carro.marca} {carro.modelo} (status: {carro.status})")
                    self.salvar_carro(carro, equipe.id)

            # Depois salvar a equipe (incluindo carro_id do carro ativo)
            conn = self._get_conn()
            cursor = conn.cursor()

            senha = equipe.senha if hasattr(equipe, 'senha') else ''  # Adiciona a senha, se existir
            serie = equipe.serie if hasattr(equipe, 'serie') else 'A'  # Série padrão A
            carro_id = equipe.carro.id if equipe.carro else None
            print(f"[DB] INSERT/REPLACE equipes: {equipe.id}, {equipe.nome}, Série: {serie}, Carro: {carro_id}")
            if self._column_exists('equipes', 'carro_id'):
                cursor.execute('''
                    INSERT INTO equipes (id, nome, serie, doricoins, senha, carro_id)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    ON DUPLICATE KEY UPDATE
                    nome = VALUES(nome),
                    serie = VALUES(serie),
                    doricoins = VALUES(doricoins),
                    senha = VALUES(senha),
                    carro_id = VALUES(carro_id)
                ''', (equipe.id, equipe.nome, serie, equipe.doricoins, senha, carro_id))
            else:
                cursor.execute('''
                    INSERT INTO equipes (id, nome, serie, doricoins, senha)
                    VALUES (%s, %s, %s, %s, %s)
                    ON DUPLICATE KEY UPDATE
                    nome = VALUES(nome),
                    serie = VALUES(serie),
                    doricoins = VALUES(doricoins),
                    senha = VALUES(senha)
                ''', (equipe.id, equipe.nome, serie, equipe.doricoins, senha))

            print(f"[DB] COMMIT banco de dados...")
            conn.commit()

            # Verificar se a equipe foi realmente inserida
            cursor.execute('SELECT * FROM equipes WHERE id = %s', (equipe.id,))
            result = cursor.fetchone()
            if result:
                print(f"[DB] Equipe salva com sucesso: {result}")
            else:
                print(f"[DB] ERRO: Equipe {equipe.id} não foi encontrada após o INSERT!")

            conn.close()
            return True
        except Exception as e:
            print(f"[DB ERRO] Erro ao salvar equipe: {e}")
            traceback.print_exc()
            return False

    def salvar_carro(self, carro: Carro, equipe_id: str = "", variacao_carro_id: str = None) -> bool:
        """Salva um carro no banco de dados (nova arquitetura: peças APENAS na tabela pecas)"""
        try:
            print(f"[DB-CARRO] Salvando carro {carro.marca} {carro.modelo} (ID: {carro.id})...")
            conn = self._get_conn()
            cursor = conn.cursor()

            # Obter modelo_id
            modelo_id = getattr(carro, 'modelo_id', None)

            # Obter status e timestamps do carro (NULL se vazio para colunas TIMESTAMP)
            status = getattr(carro, 'status', 'ativo')
            _ta = getattr(carro, 'timestamp_ativo', None)
            _tr = getattr(carro, 'timestamp_repouso', None)
            timestamp_ativo = _ta if _ta else None
            timestamp_repouso = _tr if _tr else None

            print(f"[DB-CARRO]   Status: {status}")
            print(f"[DB-CARRO]   Número: {carro.numero_carro}")
            print(f"[DB-CARRO]   Equipe ID: {equipe_id}")
            print(f"[DB-CARRO]   Modelo ID: {modelo_id}")
            print(f"[DB-CARRO]   Variação ID: {variacao_carro_id}")

            # INSERT do carro (numero_carro é UNIQUE; variacao_carro_id pode não existir em DB antigos)
            tem_variacao_col = self._column_exists('carros', 'variacao_carro_id')
            cols = 'id, numero_carro, marca, modelo, modelo_id, batidas_totais, vitoria, derrotas, empates, status, timestamp_ativo, timestamp_repouso, equipe_id'
            vals = '%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s'
            upds = '''numero_carro = VALUES(numero_carro), marca = VALUES(marca), modelo = VALUES(modelo), modelo_id = VALUES(modelo_id),
                batidas_totais = VALUES(batidas_totais), vitoria = VALUES(vitoria), derrotas = VALUES(derrotas), empates = VALUES(empates),
                status = VALUES(status), timestamp_ativo = VALUES(timestamp_ativo), timestamp_repouso = VALUES(timestamp_repouso), equipe_id = VALUES(equipe_id)'''
            if tem_variacao_col:
                cols += ', variacao_carro_id'
                vals += ', %s'
                upds += ', variacao_carro_id = VALUES(variacao_carro_id)'
            params_base = (carro.id, carro.numero_carro, carro.marca, carro.modelo, modelo_id,
                          carro.batidas_totais, carro.vitoria, carro.derrotas, carro.empates,
                          status, timestamp_ativo, timestamp_repouso, equipe_id)
            params = params_base + (variacao_carro_id,) if tem_variacao_col else params_base

            for _ in range(2):
                try:
                    cursor.execute('''
                        INSERT INTO carros (''' + cols + ''')
                        VALUES (''' + vals + ''')
                        ON DUPLICATE KEY UPDATE ''' + upds,
                        params)
                    break
                except Exception as ins_err:
                    err_msg = str(ins_err).lower()
                    if '1062' in err_msg or ('duplicate' in err_msg and 'unique' in err_msg):
                        cursor.execute('SELECT COALESCE(MAX(numero_carro), 0) + 1 FROM carros')
                        carro.numero_carro = cursor.fetchone()[0]
                        params_base = (carro.id, carro.numero_carro, carro.marca, carro.modelo, modelo_id,
                                      carro.batidas_totais, carro.vitoria, carro.derrotas, carro.empates,
                                      status, timestamp_ativo, timestamp_repouso, equipe_id)
                        params = params_base + (variacao_carro_id,) if tem_variacao_col else params_base
                        print(f"[DB-CARRO] numero_carro em conflito, usando {carro.numero_carro}")
                    else:
                        raise
            print(f"[DB-CARRO] INSERT/REPLACE carro executado")

            # Commit do carro antes de salvar as peças
            print(f"[DB-CARRO] Fazendo commit do carro...")
            conn.commit()

            # Verificar se o carro foi realmente inserido
            cursor.execute('SELECT id, marca, modelo FROM carros WHERE id = %s', (carro.id,))
            result = cursor.fetchone()
            if not result:
                print(f"[DB-CARRO] ERRO: Carro {carro.id} não foi inserido!")
                conn.close()
                return False

            # Salvar todas as peças (opcional: se falhar, carro já está salvo)
            pecas_list = carro.get_todas_pecas()
            print(f"[DB-CARRO] Salvando {len(pecas_list)} peças...")
            try:
                for peca in pecas_list:
                    peca_id_unico = f"{carro.id}_{peca.id}"
                    cursor.execute('SELECT id FROM pecas_loja WHERE id = %s', (peca.id,))
                    peca_loja_id = peca.id if cursor.fetchone() else None
                    cursor.execute('''
                        INSERT INTO pecas 
                        (id, carro_id, peca_loja_id, nome, tipo, durabilidade_maxima, durabilidade_atual, preco, coeficiente_quebra, instalado, equipe_id)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, 1, %s)
                        ON DUPLICATE KEY UPDATE
                        carro_id = VALUES(carro_id),
                        peca_loja_id = VALUES(peca_loja_id),
                        nome = VALUES(nome),
                        tipo = VALUES(tipo),
                        durabilidade_maxima = VALUES(durabilidade_maxima),
                        durabilidade_atual = VALUES(durabilidade_atual),
                        preco = VALUES(preco),
                        coeficiente_quebra = VALUES(coeficiente_quebra),
                        instalado = 1,
                        equipe_id = VALUES(equipe_id)
                    ''', (peca_id_unico, carro.id, peca_loja_id, peca.nome, peca.tipo,
                          peca.durabilidade_maxima, peca.durabilidade_atual, peca.preco, peca.coeficiente_quebra, equipe_id))
                conn.commit()
            except Exception as ep:
                print(f"[DB-CARRO] Aviso: falha ao salvar peças (carro já gravado): {ep}")
                traceback.print_exc()
                conn.rollback()
            conn.close()
            print(f"[DB-CARRO] Carro {carro.marca} {carro.modelo} salvo com sucesso!")
            return True
        except Exception as e:
            print(f"[DB-CARRO ERRO] Erro ao salvar carro: {e}")
            traceback.print_exc()
            self._ultimo_erro_carro = str(e)
            return False

    def salvar_piloto(self, piloto: Piloto) -> bool:
        """Salva um piloto no banco de dados"""
        try:
            conn = self._get_conn()
            cursor = conn.cursor()

            cursor.execute('''
                INSERT INTO pilotos 
                (id, nome, equipe_id, vitoria, derrotas, empates)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                nome = VALUES(nome),
                equipe_id = VALUES(equipe_id),
                vitoria = VALUES(vitoria),
                derrotas = VALUES(derrotas),
                empates = VALUES(empates)
            ''', (piloto.id, piloto.nome, piloto.equipe_id,
                  piloto.vitoria, piloto.derrotas, piloto.empates))

            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"Erro ao salvar piloto: {e}")
            return False

    def salvar_batalha(self, batalha: Batalha) -> bool:
        """Salva uma batalha no banco de dados"""
        try:
            conn = self._get_conn()
            cursor = conn.cursor()

            resultado = batalha.resultado.value if batalha.resultado else None

            cursor.execute('''
                INSERT INTO batalhas 
                (id, piloto_a_id, piloto_b_id, equipe_a_id, equipe_b_id, etapa, data, resultado, 
                 empates_ate_vencer, doricoins_vencedor, desgaste_base)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                piloto_a_id = VALUES(piloto_a_id),
                piloto_b_id = VALUES(piloto_b_id),
                equipe_a_id = VALUES(equipe_a_id),
                equipe_b_id = VALUES(equipe_b_id),
                etapa = VALUES(etapa),
                data = VALUES(data),
                resultado = VALUES(resultado),
                empates_ate_vencer = VALUES(empates_ate_vencer),
                doricoins_vencedor = VALUES(doricoins_vencedor),
                desgaste_base = VALUES(desgaste_base)
            ''', (batalha.id, batalha.piloto_a_id, batalha.piloto_b_id,
                  batalha.equipe_a_id, batalha.equipe_b_id, batalha.etapa,
                  batalha.data.isoformat(), resultado,
                  batalha.empates_ate_vencer, batalha.doricoins_vencedor, batalha.desgaste_base))

            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"Erro ao salvar batalha: {e}")
            return False

    def carregar_carros_por_equipe(self, equipe_id: str) -> List[Carro]:
        """Carrega todos os carros associados a uma equipe"""
        try:
            conn = self._get_conn()
            cursor = conn.cursor()

            # Carregar todos os carros da equipe (SEM colunas de ID de peças)
            cursor.execute('''
                SELECT id, numero_carro, marca, modelo, modelo_id, batidas_totais, vitoria, derrotas, empates, status, timestamp_ativo, timestamp_repouso
                FROM carros WHERE equipe_id = %s
            ''', (equipe_id,))

            carros_rows = cursor.fetchall()
            carros = []

            for carro_row in carros_rows:
                carro_id, numero, marca, modelo, modelo_id, batidas, vit, der, emp, status, timestamp_ativo, timestamp_repouso = carro_row

                # Carregar APENAS as peças instaladas (instalado = 1) do carro
                cursor.execute('''
                    SELECT id, nome, tipo, durabilidade_maxima, durabilidade_atual, preco, coeficiente_quebra
                    FROM pecas WHERE carro_id = %s AND instalado = 1
                ''', (carro_id,))

                pecas_rows = cursor.fetchall()

                # Reconstruir as peças
                pecas_map = {}
                diferenciais = []

                for peca_id, nome, tipo, dur_max, dur_atual, preco, coef_quebra in pecas_rows:
                    coeficiente = coef_quebra if coef_quebra is not None else 1.0
                    peca = Peca(
                        id=peca_id,
                        nome=nome,
                        tipo=tipo,
                        durabilidade_maxima=dur_max,
                        durabilidade_atual=dur_atual,
                        preco=preco,
                        coeficiente_quebra=coeficiente
                    )

                    if tipo == 'diferencial':
                        diferenciais.append(peca)
                    else:
                        pecas_map[tipo] = peca

                # Reconstruir o carro com as peças
                carro = Carro(
                    id=carro_id,
                    numero_carro=numero,
                    marca=marca,
                    modelo=modelo,
                    motor=pecas_map.get('motor'),
                    cambio=pecas_map.get('cambio'),
                    kit_angulo=pecas_map.get('kit_angulo'),
                    suspensao=pecas_map.get('suspensao'),
                    diferenciais=diferenciais,
                    pecas_instaladas=[],
                    status=status if status else 'ativo',
                    timestamp_ativo=timestamp_ativo if timestamp_ativo else '',
                    timestamp_repouso=timestamp_repouso if timestamp_repouso else ''
                )
                carro.modelo_id = modelo_id
                carro.motor_id = ''  # Já não existe
                carro.cambio_id = ''  # Já não existe
                carro.suspensao_id = ''  # Já não existe
                carro.kit_angulo_id = ''  # Já não existe
                carro.diferencial_id = ''  # Já não existe
                carro.batidas_totais = batidas
                carro.vitoria = vit
                carro.derrotas = der
                carro.empates = emp
                
                # Reconstruir pecas_instaladas com os dados das peças instaladas
                carro.pecas_instaladas = []
                if carro.motor:
                    carro.pecas_instaladas.append({
                        'id': carro.motor.id,
                        'nome': carro.motor.nome,
                        'tipo': 'motor'
                    })
                if carro.cambio:
                    carro.pecas_instaladas.append({
                        'id': carro.cambio.id,
                        'nome': carro.cambio.nome,
                        'tipo': 'cambio'
                    })
                if carro.kit_angulo:
                    carro.pecas_instaladas.append({
                        'id': carro.kit_angulo.id,
                        'nome': carro.kit_angulo.nome,
                        'tipo': 'kit_angulo'
                    })
                if carro.suspensao:
                    carro.pecas_instaladas.append({
                        'id': carro.suspensao.id,
                        'nome': carro.suspensao.nome,
                        'tipo': 'suspensao'
                    })

                carros.append(carro)

            conn.close()
            return carros
        except Exception as e:
            print(f"Erro ao carregar carros por equipe: {e}")
            return []

    def obter_max_numero_carro_equipe(self, equipe_id: str) -> Optional[int]:
        """Obtém o maior numero_carro para uma equipe"""
        try:
            conn = self._get_conn()
            cursor = conn.cursor()
            cursor.execute('SELECT MAX(numero_carro) FROM carros WHERE equipe_id = %s', (equipe_id,))
            result = cursor.fetchone()
            conn.close()
            return result[0] if result and result[0] is not None else None
        except Exception as e:
            print(f"[DB] Erro ao obter max numero_carro: {e}")
            return None

    def carregar_equipe(self, equipe_id: str) -> Optional[Equipe]:
        """Carrega uma equipe do banco de dados"""
        try:
            conn = self._get_conn()
            cursor = conn.cursor()

            if self._column_exists('equipes', 'carro_id'):
                cursor.execute('SELECT id, nome, serie, doricoins, senha, carro_id FROM equipes WHERE id = %s', (equipe_id,))
            else:
                cursor.execute('SELECT id, nome, serie, doricoins, senha FROM equipes WHERE id = %s', (equipe_id,))
            row = cursor.fetchone()

            if not row:
                print(f"[DB] Equipe {equipe_id} não encontrada no banco")
                conn.close()
                return None

            if len(row) >= 6:
                equipe_id, nome, serie, doricoins, senha, carro_id_atual = row[0], row[1], row[2], row[3], row[4], row[5]
            else:
                equipe_id, nome, serie, doricoins, senha = row[0], row[1], row[2], row[3], row[4]
                carro_id_atual = None

            # Carregar os carros associados à equipe
            carros = self.carregar_carros_por_equipe(equipe_id)
            
            # Encontrar o carro ativo baseado no carro_id da equipe
            carro_ativo = None
            if carro_id_atual:
                for c in carros:
                    if str(c.id) == str(carro_id_atual):
                        carro_ativo = c
                        break
            if not carro_ativo and carros:
                carro_ativo = carros[0]

            # Criar objeto Equipe
            equipe = Equipe(
                id=equipe_id,
                nome=nome,
                doricoins=doricoins,
                senha=senha,  # Adiciona a senha ao objeto Equipe
                carro=carro_ativo,
                carros=carros  # Todos os carros da equipe
            )
            equipe.serie = serie  # Atribuir série

            conn.close()
            return equipe
        except Exception as e:
            # Debug: mostrar qual é o erro
            print(f"[DB] ERRO ao carregar equipe {equipe_id}: {e}")
            return None

    def carregar_todas_equipes(self) -> list:
        """Carrega todas as equipes do banco de dados como objetos Equipe"""
        try:
            conn = self._get_conn()
            cursor = conn.cursor()

            print("[DB] Carregando equipes do banco de dados...")
            if self._column_exists('equipes', 'carro_id'):
                cursor.execute('SELECT id, nome, serie, doricoins, senha, carro_id FROM equipes')
            else:
                cursor.execute('SELECT id, nome, serie, doricoins, senha FROM equipes')
            equipes_rows = cursor.fetchall()

            equipes = []
            for row in equipes_rows:
                equipe_id, nome, serie, doricoins, senha = row[0], row[1], row[2], row[3], row[4]
                carro_id_atual = row[5] if len(row) >= 6 else None
                carros = self.carregar_carros_por_equipe(equipe_id)
                carro = None
                if carro_id_atual:
                    for c in carros:
                        if str(c.id) == str(carro_id_atual):
                            carro = c
                            break
                if not carro and carros:
                    carro = carros[0]

                # Criar objeto Equipe
                equipe = Equipe(
                    id=equipe_id,
                    nome=nome,
                    doricoins=doricoins,
                    senha=senha if senha else "123456",
                    carro=carro,
                    carros=carros  # Todos os carros da equipe
                )
                equipe.serie = serie  # Atribuir série
                equipes.append(equipe)

            conn.close()
            return equipes
        except Exception as e:
            print(f"[DB ERRO] Erro ao carregar equipes: {e}")
            traceback.print_exc()
            return []

    def _carregar_todos_carros_equipe(self, equipe_id: str) -> List[Carro]:
        """Carrega todos os carros associados a uma equipe"""
        try:
            conn = self._get_conn()
            cursor = conn.cursor()

            # Carregar todos os carros da equipe pelo equipe_id
            cursor.execute('SELECT id FROM carros WHERE equipe_id = %s ORDER BY numero_carro', (equipe_id,))
            carro_ids = cursor.fetchall()

            conn.close()

            carros_list = []
            for (carro_id,) in carro_ids:
                carro = self._carregar_carro_por_id(carro_id)
                if carro:
                    carros_list.append(carro)
            
            return carros_list
        except Exception as e:
            print(f"Erro ao carregar carros da equipe: {e}")
            return []

    def _carregar_carro_por_id(self, carro_id: str) -> Optional[Carro]:
        """Carrega um carro pelo seu ID"""
        try:
            conn = self._get_conn()
            cursor = conn.cursor()

            # Carregar o carro (SEM as colunas de ID de peças)
            cursor.execute('''
                SELECT id, numero_carro, marca, modelo, modelo_id, batidas_totais, vitoria, derrotas, empates, status, timestamp_ativo, timestamp_repouso
                FROM carros WHERE id = %s
            ''', (carro_id,))

            carro_row = cursor.fetchone()
            if not carro_row:
                conn.close()
                return None

            carro_id, numero, marca, modelo, modelo_id, batidas, vit, der, emp, status, timestamp_ativo, timestamp_repouso = carro_row

            # Carregar APENAS as peças instaladas (instalado = 1) do carro
            cursor.execute('''
                SELECT id, nome, tipo, durabilidade_maxima, durabilidade_atual, preco, coeficiente_quebra
                FROM pecas WHERE carro_id = %s AND instalado = 1
            ''', (carro_id,))

            pecas_rows = cursor.fetchall()
            conn.close()

            # Reconstruir as peças
            pecas_map = {}
            diferenciais = []

            for peca_id, nome, tipo, dur_max, dur_atual, preco, coef_quebra in pecas_rows:
                coeficiente = coef_quebra if coef_quebra is not None else 1.0
                peca = Peca(
                    id=peca_id,
                    nome=nome,
                    tipo=tipo,
                    durabilidade_maxima=dur_max,
                    durabilidade_atual=dur_atual,
                    preco=preco,
                    coeficiente_quebra=coeficiente
                )

                if tipo == 'diferencial':
                    diferenciais.append(peca)
                else:
                    pecas_map[tipo] = peca

            # Reconstruir o carro com as peças
            carro = Carro(
                id=carro_id,
                numero_carro=numero,
                marca=marca,
                modelo=modelo,
                motor=pecas_map.get('motor'),
                cambio=pecas_map.get('cambio'),
                kit_angulo=pecas_map.get('kit_angulo'),
                suspensao=pecas_map.get('suspensao'),
                diferenciais=diferenciais,
                pecas_instaladas=[],
                status=status if status else 'ativo',
                timestamp_ativo=timestamp_ativo if timestamp_ativo else '',
                timestamp_repouso=timestamp_repouso if timestamp_repouso else ''
            )
            
            # Preencher pecas_instaladas com todas as peças encontradas
            for tipo, peca in pecas_map.items():
                if peca:
                    carro.pecas_instaladas.append({
                        'id': peca.id,
                        'nome': peca.nome,
                        'tipo': peca.tipo
                    })
            for peca in diferenciais:
                carro.pecas_instaladas.append({
                    'id': peca.id,
                    'nome': peca.nome,
                    'tipo': peca.tipo
                })
            carro.modelo_id = modelo_id
            carro.motor_id = ''  # Já não existe
            carro.cambio_id = ''  # Já não existe
            carro.suspensao_id = ''  # Já não existe
            carro.kit_angulo_id = ''  # Já não existe
            carro.diferencial_id = ''  # Já não existe
            carro.batidas_totais = batidas
            carro.vitoria = vit
            carro.derrotas = der
            carro.empates = emp

            return carro
        except Exception as e:
            print(f"Erro ao carregar carro por ID: {e}")
            return None

    def carregar_carro(self, carro_id: str) -> Optional[Carro]:
        """Carrega um carro pelo seu ID (método público)"""
        return self._carregar_carro_por_id(carro_id)

    def deletar_equipe(self, equipe_id: str) -> bool:
        """Deleta uma equipe do banco de dados"""
        try:
            conn = self._get_conn()
            cursor = conn.cursor()
            cursor.execute('DELETE FROM equipes WHERE id = %s', (equipe_id,))
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"Erro ao deletar equipe: {e}")
            return False

    def apagar_equipe(self, equipe_id: str) -> bool:
        """Apaga uma equipe do banco de dados"""
        try:
            conn = self._get_conn()
            cursor = conn.cursor()
            
            # Primeiro, deletar todos os pilotos da equipe
            cursor.execute('DELETE FROM pilotos WHERE equipe_id = %s', (equipe_id,))
            
            # Depois, deletar todos os carros da equipe (isso também deletará as peças)
            cursor.execute('DELETE FROM carros WHERE equipe_id = %s', (equipe_id,))
            
            # Por fim, deletar a equipe
            cursor.execute('DELETE FROM equipes WHERE id = %s', (equipe_id,))
            
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"Erro ao apagar equipe: {e}")
            return False

    def apagar_carro(self, carro_id: str) -> bool:
        """Apaga um carro do banco de dados"""
        try:
            conn = self._get_conn()
            cursor = conn.cursor()
            
            # Primeiro, deletar todas as peças associadas ao carro
            cursor.execute('DELETE FROM pecas WHERE carro_id = %s', (carro_id,))
            
            # Depois, deletar o carro
            cursor.execute('DELETE FROM carros WHERE id = %s', (carro_id,))
            
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"Erro ao apagar carro: {e}")
            return False

    def apagar_piloto(self, piloto_id: str) -> bool:
        """Apaga um piloto do banco de dados"""
        try:
            conn = self._get_conn()
            cursor = conn.cursor()
            cursor.execute('DELETE FROM pilotos WHERE id = %s', (piloto_id,))
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"Erro ao apagar piloto: {e}")
            return False

    def cadastrar_piloto(self, nome: str, senha: str) -> dict:
        """Cadastra um novo piloto sem equipe"""
        try:
            import uuid
            from werkzeug.security import generate_password_hash
            
            piloto_id = str(uuid.uuid4())
            senha_hash = generate_password_hash(senha)
            
            conn = self._get_conn()
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO pilotos (id, nome, senha, equipe_id)
                VALUES (%s, %s, %s, NULL)
            ''', (piloto_id, nome, senha_hash))
            
            conn.commit()
            cursor.close()
            conn.close()
            
            print(f"[DB] Piloto cadastrado: {nome} ({piloto_id})")
            return {
                'sucesso': True,
                'piloto_id': piloto_id,
                'nome': nome
            }
        except Exception as e:
            print(f"[DB] Erro ao cadastrar piloto: {e}")
            return {
                'sucesso': False,
                'erro': str(e)
            }

    def autenticar_piloto(self, nome: str, senha: str) -> dict:
        """Autentica um piloto pelo nome e senha"""
        try:
            from werkzeug.security import check_password_hash
            
            conn = self._get_conn()
            cursor = conn.cursor(dictionary=True)
            
            cursor.execute('SELECT id, nome, senha FROM pilotos WHERE nome = %s', (nome,))
            piloto = cursor.fetchone()
            cursor.close()
            conn.close()
            
            if not piloto:
                return {'sucesso': False, 'erro': 'Piloto não encontrado'}
            
            if check_password_hash(piloto['senha'], senha):
                return {
                    'sucesso': True,
                    'piloto_id': piloto['id'],
                    'nome': piloto['nome']
                }
            else:
                return {'sucesso': False, 'erro': 'Piloto ou senha incorreta'}
        except Exception as e:
            print(f"[DB] Erro ao autenticar piloto: {e}")
            return {'sucesso': False, 'erro': str(e)}

    def exportar_json(self, arquivo: str = "data/backup.json") -> bool:
        """Exporta todos os dados para um arquivo JSON"""
        try:
            conn = self._get_conn()
            cursor = conn.cursor()

            def row_to_dict(cursor, row):
                """Converte uma linha em dicionário"""
                columns = [desc[0] for desc in cursor.description]
                return dict(zip(columns, row))

            dados = {
                'equipes': [row_to_dict(cursor, row) for row in cursor.execute('SELECT * FROM equipes').fetchall()],
                'carros': [row_to_dict(cursor, row) for row in cursor.execute('SELECT * FROM carros').fetchall()],
                'pecas': [row_to_dict(cursor, row) for row in cursor.execute('SELECT * FROM pecas').fetchall()],
                'pilotos': [row_to_dict(cursor, row) for row in cursor.execute('SELECT * FROM pilotos').fetchall()],
                'batalhas': [row_to_dict(cursor, row) for row in cursor.execute('SELECT * FROM batalhas').fetchall()],
                'etapas': [row_to_dict(cursor, row) for row in cursor.execute('SELECT * FROM etapas').fetchall()],
            }

            conn.close()

            Path(arquivo).parent.mkdir(parents=True, exist_ok=True)
            with open(arquivo, 'w', encoding='utf-8') as f:
                json.dump(dados, f, ensure_ascii=False, indent=2)

            return True
        except Exception as e:
            print(f"Erro ao exportar JSON: {e}")
            return False

    # ============ LOJA DE CARROS ============

    def salvar_modelo_loja(self, modelo, imagem_base64=None) -> bool:
        """Salva um modelo de carro da loja no banco de dados junto com suas variações"""
        try:
            conn = self._get_conn()
            cursor = conn.cursor()

            # Obter imagem do objeto modelo se não foi fornecida
            if imagem_base64 is None:
                imagem_base64 = getattr(modelo, 'imagem', None)
            
            if imagem_base64:
                print(f"[DB SALVAR MODELO] Salvando imagem: tipo={type(imagem_base64).__name__}, tamanho={len(imagem_base64) if isinstance(imagem_base64, (str, bytes)) else 'N/A'}")
                if isinstance(imagem_base64, bytes):
                    base64_str = base64.b64encode(imagem_base64).decode('utf-8')
                    imagem_base64 = 'data:image/jpeg;base64,' + base64_str
                    print(f"[DB SALVAR MODELO] Convertido bytes para string data:image: tamanho={len(imagem_base64)}")
                elif isinstance(imagem_base64, str):
                    print(f"[DB SALVAR MODELO] Preview: {imagem_base64[:100]}")
                    if not imagem_base64.startswith('data:image'):
                        imagem_base64 = 'data:image/jpeg;base64,' + imagem_base64
                        print(f"[DB SALVAR MODELO] Adicionado prefixo, novo tamanho={len(imagem_base64)}")
                
                # Comprimir imagem se for muito grande (maior que 500KB)
                if len(imagem_base64) > 500000:
                    print(f"[DB SALVAR MODELO] Imagem muito grande ({len(imagem_base64)} bytes), comprimindo...")
                    try:
                        import io
                        from PIL import Image
                        
                        # Extrair base64 puro (remover prefixo)
                        if imagem_base64.startswith('data:image/jpeg;base64,'):
                            base64_puro = imagem_base64.replace('data:image/jpeg;base64,', '')
                        else:
                            base64_puro = imagem_base64
                        
                        # Decodificar base64
                        imagem_bytes = base64.b64decode(base64_puro)
                        img = Image.open(io.BytesIO(imagem_bytes))
                        
                        # Redimensionar para max 1920x1920
                        img.thumbnail((1920, 1920), Image.Resampling.LANCZOS)
                        
                        # Salvar com compressão (qualidade 70)
                        buffer = io.BytesIO()
                        img.save(buffer, format='JPEG', quality=70, optimize=True)
                        imagem_comprimida = buffer.getvalue()
                        
                        # Converter de volta para base64
                        base64_comprimido = base64.b64encode(imagem_comprimida).decode('utf-8')
                        imagem_base64 = 'data:image/jpeg;base64,' + base64_comprimido
                        
                        print(f"[DB SALVAR MODELO] Imagem comprimida: {len(imagem_comprimida)} bytes (base64: {len(imagem_base64)} bytes)")
                    except Exception as e:
                        print(f"[DB SALVAR MODELO] Erro ao comprimir imagem: {e}, usando original")
            else:
                print(f"[DB SALVAR MODELO] Nenhuma imagem a salvar")
                imagem_base64 = None

            # Salvar modelo (sem motor/câmbio/peças que agora estão em variacoes)
            cursor.execute('''
                INSERT INTO modelos_carro_loja
                (id, marca, modelo, classe, preco, descricao, imagem)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                marca = VALUES(marca),
                modelo = VALUES(modelo),
                classe = VALUES(classe),
                preco = VALUES(preco),
                descricao = VALUES(descricao),
                imagem = VALUES(imagem)
            ''', (modelo.id, modelo.marca, modelo.modelo, modelo.classe, modelo.preco,
                  modelo.descricao, imagem_base64))

            # Salvar variações do modelo
            variacoes = getattr(modelo, 'variacoes', [])
            if variacoes:
                for variacao in variacoes:
                    cursor.execute('''
                        INSERT INTO variacoes_carros
                        (id, modelo_carro_loja_id, motor_id, cambio_id, suspensao_id, kit_angulo_id, diferencial_id, valor)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                        ON DUPLICATE KEY UPDATE
                        motor_id = VALUES(motor_id),
                        cambio_id = VALUES(cambio_id),
                        suspensao_id = VALUES(suspensao_id),
                        kit_angulo_id = VALUES(kit_angulo_id),
                        diferencial_id = VALUES(diferencial_id),
                        valor = VALUES(valor)
                    ''', (variacao.id, variacao.modelo_carro_loja_id, variacao.motor_id, variacao.cambio_id,
                          variacao.suspensao_id, variacao.kit_angulo_id, variacao.diferencial_id, variacao.valor))

            conn.commit()
            
            # DEBUG: Verificar
            cursor.execute('SELECT imagem FROM modelos_carro_loja WHERE id = %s', (modelo.id,))
            row_check = cursor.fetchone()
            if row_check and row_check[0]:
                img_salva = row_check[0]
                tamanho_salvo = len(img_salva) if isinstance(img_salva, (str, bytes)) else 0
                print(f"[DB SALVAR MODELO] Verificação pós-salvamento: tamanho em BD = {tamanho_salvo}")
                if imagem_base64 and tamanho_salvo != len(imagem_base64):
                    print(f"[DB SALVAR MODELO] ⚠️ AVISO: Tamanho original={len(imagem_base64)}, tamanho salvo={tamanho_salvo}")
            
            print(f"[DB SALVAR MODELO] Modelo salvo com {len(variacoes)} variação(ões)")
            conn.close()
            return True
        except Exception as e:
            print(f"Erro ao salvar modelo: {e}")
            import traceback
            traceback.print_exc()
            return False

    def carregar_modelos_loja(self):
        """Carrega apenas modelos que possuem variações cadastradas na tabela variacoes_carros"""
        try:
            conn = self._get_conn()
            cursor = conn.cursor()

            # Importar aqui para evitar circular import
            from .loja_carros import ModeloCarro, VariacaoCarro
            
            # Carregar apenas modelos que têm variações (INNER JOIN)
            cursor.execute('''
                SELECT DISTINCT m.id, m.marca, m.modelo, m.classe, m.preco, m.descricao, m.data_criacao, m.imagem 
                FROM modelos_carro_loja m
                INNER JOIN variacoes_carros v ON m.id = v.modelo_carro_loja_id
                ORDER BY m.data_criacao DESC
            ''')
            rows = cursor.fetchall()
            
            modelos = []
            
            for row in rows:
                modelo_id = row[0]
                imagem = row[7] if len(row) > 7 else None
                
                # Converter imagem se necessário
                if imagem:
                    if isinstance(imagem, bytes):
                        try:
                            base64_str = base64.b64encode(imagem).decode('utf-8')
                            imagem = 'data:image/jpeg;base64,' + base64_str
                            print(f"[CARREGAR MODELOS] {row[2]}: bytes convertidos para base64 (tamanho={len(imagem)})")
                        except Exception as e:
                            print(f"[AVISO] Erro ao converter imagem do modelo {modelo_id}: {e}")
                            imagem = None
                    elif isinstance(imagem, str):
                        if imagem.startswith('data:image/jpeg;base64,ZGF0YTp'):
                            print(f"[CORRIGIR IMAGEM] {row[2]}: Detectado base64 duplo, decodificando...")
                            try:
                                base64_parte = imagem.split(',', 1)[1]
                                imagem = base64.b64decode(base64_parte).decode('utf-8')
                                print(f"[CORRIGIR IMAGEM] {row[2]}: Corrigido, novo tamanho={len(imagem)}")
                            except Exception as e:
                                print(f"[ERRO CORRIGIR] {row[2]}: {e}")
                                imagem = None
                        elif not imagem.startswith('data:image'):
                            imagem = 'data:image/jpeg;base64,' + imagem
                
                # Carregar variações deste modelo
                cursor.execute('''
                    SELECT id, motor_id, cambio_id, suspensao_id, kit_angulo_id, diferencial_id, valor
                    FROM variacoes_carros
                    WHERE modelo_carro_loja_id = %s
                ''', (modelo_id,))
                variacao_rows = cursor.fetchall()
                
                variacoes = []
                for var_row in variacao_rows:
                    variacao = VariacaoCarro(
                        id=var_row[0],
                        modelo_carro_loja_id=modelo_id,
                        motor_id=var_row[1],
                        cambio_id=var_row[2],
                        suspensao_id=var_row[3],
                        kit_angulo_id=var_row[4],
                        diferencial_id=var_row[5],
                        valor=var_row[6] if len(var_row) > 6 else 0.0
                    )
                    variacoes.append(variacao)
                
                # Criar modelo
                modelo = ModeloCarro(
                    id=modelo_id,
                    marca=row[1],
                    modelo=row[2],
                    classe=row[3],
                    preco=row[4],
                    descricao=row[5],
                    imagem=imagem,
                    variacoes=variacoes
                )
                
                if imagem:
                    tamanho = len(imagem) if isinstance(imagem, (str, bytes)) else 0
                    print(f"[CARREGAR MODELOS] {modelo.modelo}: imagem atribuída (tipo={type(imagem).__name__}, tamanho={tamanho})")
                else:
                    print(f"[CARREGAR MODELOS] {modelo.modelo}: SEM imagem, variações={len(variacoes)}")
                
                modelos.append(modelo)
            
            conn.close()
            return modelos
        except Exception as e:
            print(f"Erro ao carregar modelos: {e}")
            return []

    def buscar_modelo_loja_por_id(self, modelo_id: str):
        """Busca um modelo de carro da loja por ID"""
        try:
            conn = self._get_conn()
            cursor = conn.cursor()

            cursor.execute('SELECT * FROM modelos_carro_loja WHERE id = %s', (modelo_id,))
            row = cursor.fetchone()
            conn.close()

            if row:
                # Importar aqui para evitar circular import
                from .loja_carros import ModeloCarro
                
                # Verificar se as novas colunas existem (para compatibilidade com dados antigos)
                motor_id = row[6] if len(row) > 6 and row[6] is not None else None
                cambio_id = row[7] if len(row) > 7 and row[7] is not None else None
                suspensao_id = row[8] if len(row) > 8 and row[8] is not None else None
                kit_angulo_id = row[9] if len(row) > 9 and row[9] is not None else None
                diferencial_id = row[10] if len(row) > 10 and row[10] is not None else None
                
                return ModeloCarro(
                    id=row[0],
                    marca=row[1],
                    modelo=row[2],
                    classe=row[3],
                    preco=row[4],
                    descricao=row[5],
                    motor_id=motor_id,
                    cambio_id=cambio_id,
                    suspensao_id=suspensao_id,
                    kit_angulo_id=kit_angulo_id,
                    diferencial_id=diferencial_id
                )
            return None
        except Exception as e:
            print(f"Erro ao buscar modelo por ID {modelo_id}: {e}")
            return None

    def buscar_variacao_carro_por_id(self, variacao_id: str) -> dict:
        """Busca uma variação de carro da loja por ID"""
        try:
            conn = self._get_conn()
            cursor = conn.cursor()

            cursor.execute('''
                SELECT id, modelo_carro_loja_id, motor_id, cambio_id, suspensao_id, kit_angulo_id, diferencial_id, valor
                FROM variacoes_carros 
                WHERE id = %s
            ''', (variacao_id,))
            row = cursor.fetchone()
            conn.close()

            if row:
                return {
                    'id': row[0],
                    'modelo_carro_loja_id': row[1],
                    'motor_id': row[2],
                    'cambio_id': row[3],
                    'suspensao_id': row[4],
                    'kit_angulo_id': row[5],
                    'diferencial_id': row[6],
                    'valor': row[7] if len(row) > 7 else 0.0
                }
            return None
        except Exception as e:
            print(f"Erro ao buscar variação por ID {variacao_id}: {e}")
            return None

    def deletar_modelo_loja(self, modelo_id: str) -> bool:
        """Deleta um modelo de carro da loja no banco de dados"""
        try:
            conn = self._get_conn()
            cursor = conn.cursor()
            cursor.execute('DELETE FROM modelos_carro_loja WHERE id = %s', (modelo_id,))
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"Erro ao deletar modelo: {e}")
            return False

    # ============ LOJA DE PECAS ============

    def salvar_peca_loja(self, peca, imagem_base64=None) -> bool:
        """Salva uma peca da loja no banco de dados"""
        try:
            conn = self._get_conn()
            cursor = conn.cursor()

            # Obter imagem do objeto peca se não foi fornecida
            if imagem_base64 is None:
                imagem_base64 = getattr(peca, 'imagem', None)
            
            # Comprimir imagem se for muito grande (maior que 500KB)
            if imagem_base64 and len(str(imagem_base64)) > 500000:
                print(f"[DB SALVAR PECA] Imagem muito grande ({len(str(imagem_base64))} bytes), comprimindo...")
                try:
                    import io
                    from PIL import Image
                    
                    # Extrair base64 puro (remover prefixo)
                    if isinstance(imagem_base64, str):
                        if imagem_base64.startswith('data:image/jpeg;base64,'):
                            base64_puro = imagem_base64.replace('data:image/jpeg;base64,', '')
                        elif imagem_base64.startswith('data:image/png;base64,'):
                            base64_puro = imagem_base64.replace('data:image/png;base64,', '')
                        else:
                            base64_puro = imagem_base64
                    else:
                        base64_puro = imagem_base64
                    
                    # Decodificar base64
                    imagem_bytes = base64.b64decode(base64_puro) if isinstance(base64_puro, str) else base64_puro
                    img = Image.open(io.BytesIO(imagem_bytes))
                    
                    # Redimensionar para max 1920x1920
                    img.thumbnail((1920, 1920), Image.Resampling.LANCZOS)
                    
                    # Salvar com compressão (qualidade 70)
                    buffer = io.BytesIO()
                    img.save(buffer, format='JPEG', quality=70, optimize=True)
                    imagem_comprimida = buffer.getvalue()
                    
                    # Converter de volta para base64
                    base64_comprimido = base64.b64encode(imagem_comprimida).decode('utf-8')
                    imagem_base64 = 'data:image/jpeg;base64,' + base64_comprimido
                    
                    print(f"[DB SALVAR PECA] Imagem comprimida: {len(imagem_comprimida)} bytes (base64: {len(imagem_base64)} bytes)")
                except Exception as e:
                    print(f"[DB SALVAR PECA] Erro ao comprimir imagem: {e}, usando original")

            values = (peca.id, peca.nome, peca.tipo, peca.preco,
                      peca.descricao, peca.compatibilidade, peca.durabilidade, peca.coeficiente_quebra, imagem_base64)
            print(f"[DEBUG] Salvando peca: {peca.id} - {peca.nome}")

            cursor.execute('''
                INSERT INTO pecas_loja 
                (id, nome, tipo, preco, descricao, compatibilidade, durabilidade, coeficiente_quebra, imagem)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                nome = VALUES(nome),
                tipo = VALUES(tipo),
                preco = VALUES(preco),
                descricao = VALUES(descricao),
                compatibilidade = VALUES(compatibilidade),
                durabilidade = VALUES(durabilidade),
                coeficiente_quebra = VALUES(coeficiente_quebra),
                imagem = VALUES(imagem)
            ''', values)

            conn.commit()
            conn.close()
            print(f"[DEBUG] Peca salva com sucesso: {peca.id}")
            return True
        except Exception as e:
            print(f"Erro ao salvar peca: {e}")
            import traceback
            traceback.print_exc()
            return False

    def carregar_pecas_loja(self):
        """Carrega todas as pecas cadastradas do banco de dados"""
        try:
            conn = self._get_conn()
            cursor = conn.cursor()

            cursor.execute('SELECT id, nome, tipo, preco, descricao, compatibilidade, durabilidade, coeficiente_quebra, imagem FROM pecas_loja')
            rows = cursor.fetchall()
            conn.close()

            pecas = []
            for row in rows:
                # Importar aqui para evitar circular import
                from .loja_pecas import PecaLoja

                # Extrair campos
                coef_quebra = row[7] if len(row) > 7 else 1.0
                imagem = row[8] if len(row) > 8 else None

                # Converter para data:image/... se necessário
                if imagem:
                    if isinstance(imagem, bytes):
                        try:
                            # Se for bytes, converter para data:image/jpeg;base64,xxx
                            base64_str = base64.b64encode(imagem).decode('utf-8')
                            imagem = 'data:image/jpeg;base64,' + base64_str
                            print(f"[CARREGAR PEÇAS] {row[1]}: bytes convertidos para base64 (tamanho={len(imagem)})")
                        except Exception as e:
                            print(f"[AVISO] Erro ao converter imagem da peca {row[0]}: {e}")
                            imagem = None
                    elif isinstance(imagem, str):
                        # Se é string, verificar se já tem o prefixo correto ou se é base64 duplo
                        if imagem.startswith('data:image/jpeg;base64,ZGF0YTp'):
                            # É base64 DUPLO! Precisa decodificar
                            print(f"[CORRIGIR IMAGEM] {row[1]}: Detectado base64 duplo, decodificando...")
                            try:
                                base64_parte = imagem.split(',', 1)[1]
                                imagem = base64.b64decode(base64_parte).decode('utf-8')
                                print(f"[CORRIGIR IMAGEM] {row[1]}: Corrigido, novo tamanho={len(imagem)}")
                            except Exception as e:
                                print(f"[ERRO CORRIGIR] {row[1]}: {e}")
                                imagem = None
                        elif not imagem.startswith('data:image'):
                            # É base64 puro sem prefixo, adicionar
                            imagem = 'data:image/jpeg;base64,' + imagem
                        # Senão, já está correto com prefixo data:image/...

                peca = PecaLoja(
                    id=row[0],
                    nome=row[1],
                    tipo=row[2],
                    preco=row[3],
                    descricao=row[4],
                    compatibilidade=row[5],
                    durabilidade=row[6],
                    coeficiente_quebra=coef_quebra if coef_quebra is not None else 1.0
                )
                # Atribuir imagem se existir
                if imagem:
                    peca.imagem = imagem
                    print(f"[CARREGAR PEÇAS] {peca.nome}: imagem atribuída (tipo={type(imagem).__name__}, tamanho={len(imagem) if isinstance(imagem, (str, bytes)) else 'N/A'})")
                    if isinstance(imagem, str):
                        print(f"[CARREGAR PEÇAS] Preview: {imagem[:80]}")
                else:
                    print(f"[CARREGAR PEÇAS] {peca.nome}: SEM imagem")
                pecas.append(peca)

            return pecas
        except Exception as e:
            print(f"Erro ao carregar pecas: {e}")
            return []

    def deletar_peca_loja(self, peca_id: str) -> bool:
        """Deleta uma peça da loja no banco de dados"""
        try:
            conn = self._get_conn()
            cursor = conn.cursor()
            cursor.execute('DELETE FROM pecas_loja WHERE id = %s', (peca_id,))
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"Erro ao deletar peca: {e}")
            return False

    def buscar_peca_loja_por_id(self, peca_id: str):
        """Busca uma peça da loja por ID"""
        try:
            conn = self._get_conn()
            cursor = conn.cursor()

            cursor.execute('SELECT * FROM pecas_loja WHERE id = %s', (peca_id,))
            row = cursor.fetchone()
            conn.close()

            if row:
                # Importar aqui para evitar circular import
                from .loja_pecas import PecaLoja

                # Extrair coeficiente_quebra se existir na linha (última coluna)
                coef_quebra = row[7] if len(row) > 7 else 1.0

                return PecaLoja(
                    id=row[0],
                    nome=row[1],
                    tipo=row[2],
                    preco=row[3],
                    descricao=row[4],
                    compatibilidade=row[5],
                    durabilidade=row[6],
                    coeficiente_quebra=coef_quebra if coef_quebra is not None else 1.0
                )
            return None
        except Exception as e:
            print(f"Erro ao buscar peca por ID: {e}")
            return None

    def carregar_pecas_armazem(self, carro_id):
        """Carrega todas as peças no armazém (instalado = 0) de um carro específico"""
        try:
            conn = self._get_conn()
            cursor = conn.cursor()

            cursor.execute('''
                SELECT p.id, p.nome, p.tipo, p.durabilidade_maxima, p.durabilidade_atual, 
                       pl.preco, p.peca_loja_id
                FROM pecas p
                LEFT JOIN pecas_loja pl ON p.peca_loja_id = pl.id
                WHERE p.carro_id = %s AND p.instalado = 0
                ORDER BY p.id DESC
            ''', (carro_id,))
            
            rows = cursor.fetchall()
            conn.close()

            pecas_armazem = []
            for row in rows:
                peca = {
                    'nome': row[1],
                    'tipo': row[2],
                    'durabilidade_maxima': row[3],
                    'durabilidade_atual': row[4],
                    'preco': row[5] or 0,
                    'durabilidade_percentual': int((row[4] / row[3] * 100) if row[3] > 0 else 0)
                }
                pecas_armazem.append(peca)

            return pecas_armazem
        except Exception as e:
            print(f"Erro ao carregar peças do armazém: {e}")
            return []

    def carregar_pecas_armazem_equipe(self, equipe_id):
        """Carrega todas as peças no armazém (instalado = 0) de uma equipe"""
        try:
            conn = self._get_conn()
            cursor = conn.cursor()

            print(f"[DB ARMAZÉM] Buscando peças com instalado=0 para equipe: {equipe_id}")
            
            # Apenas peças no armazém: instalado=0 E equipe_id correto
            cursor.execute('''
                SELECT p.id, p.nome, p.tipo, p.durabilidade_maxima, p.durabilidade_atual, 
                       COALESCE(pl.preco, p.preco), p.peca_loja_id, pl.compatibilidade
                FROM pecas p
                LEFT JOIN pecas_loja pl ON p.peca_loja_id = pl.id
                WHERE p.equipe_id = %s AND p.instalado = 0
                ORDER BY p.id DESC
            ''', (equipe_id,))
            
            rows = cursor.fetchall()
            conn.close()
            
            print(f"[DB ARMAZÉM] Query retornou {len(rows)} linhas")

            pecas_armazem = []
            for row in rows:
                # Processar compatibilidade
                compatibilidade_json = row[7] if len(row) > 7 else None
                compatibilidades = []
                
                if compatibilidade_json:
                    try:
                        if isinstance(compatibilidade_json, str):
                            import json
                            compat_data = json.loads(compatibilidade_json)
                            compatibilidades = compat_data.get('compatibilidades', [])
                        elif isinstance(compatibilidade_json, dict):
                            compatibilidades = compatibilidade_json.get('compatibilidades', [])
                    except:
                        compatibilidades = []
                
                # Se a compatibilidade é universal, retornar array vazio
                if compatibilidades and all(str(c).lower() == 'universal' for c in compatibilidades):
                    compatibilidades = []
                
                peca = {
                    'id': row[0],
                    'nome': row[1],
                    'tipo': row[2],
                    'durabilidade_maxima': row[3],
                    'durabilidade_atual': row[4],
                    'preco': row[5] or 0,
                    'durabilidade_percentual': int((row[4] / row[3] * 100) if row[3] > 0 else 0),
                    'carro_nome': 'Armazém',
                    'compatibilidades': compatibilidades  # Array de IDs de carros compatíveis (vazio = universal)
                }
                pecas_armazem.append(peca)

            print(f"[DB ARMAZÉM] Retornando {len(pecas_armazem)} peças do armazém")
            return pecas_armazem
        except Exception as e:
            print(f"Erro ao carregar peças do armazém da equipe: {e}")
            import traceback
            traceback.print_exc()
            return []

    def carregar_carros(self):
        """Carrega todos os carros da tabela carros para compatibilidade"""
        try:
            conn = self._get_conn()
            cursor = conn.cursor()

            cursor.execute('SELECT id, marca, modelo FROM carros')
            rows = cursor.fetchall()
            conn.close()

            carros = []
            for row in rows:
                # Criar um objeto simples com id, marca, modelo
                class CarroSimples:
                    def __init__(self, carro_id, marca, modelo):
                        self.id = carro_id
                        self.marca = marca
                        self.modelo = modelo

                carro = CarroSimples(row[0], row[1], row[2])
                carros.append(carro)

            return carros
        except Exception as e:
            print(f"Erro ao carregar carros: {e}")
            return []

    # ============ MÉTODOS DE PEÇAS E INSTALAÇÃO ============

    def validar_limite_peca(self, carro_id, tipo_peca):
        """Verifica se é possível instalar uma peça de um tipo no carro (máximo 1 motor, 1 câmbio, 1 suspensão, 1 kit ângulo, N diferenciais)"""
        try:
            # Limites: 1x motor, 1x câmbio, 1x suspensão, 1x kit_angulo, N diferenciais
            limites = {
                'motor': 1,
                'cambio': 1,
                'suspensao': 1,
                'kit_angulo': 1,
                'diferencial': float('inf')  # Sem limite
            }
            
            if tipo_peca not in limites:
                return True  # Tipo desconhecido, permitir
            
            limite = limites[tipo_peca]
            if limite == float('inf'):  # Sem limite (diferencial)
                return True
            
            # Contar quantas peças deste tipo estão instaladas no carro
            conn = self._get_conn()
            cursor = conn.cursor()
            cursor.execute('''
                SELECT COUNT(*) FROM pecas 
                WHERE carro_id = %s AND tipo = %s AND instalado = 1
            ''', (carro_id, tipo_peca))
            
            count = cursor.fetchone()[0]
            conn.close()
            
            return count < limite
        except Exception as e:
            print(f"Erro ao validar limite de peça: {e}")
            return False

    def obter_pecas_carro_com_compatibilidade(self, carro_id):
        """Obtém todas as peças instaladas de um carro com suas compatibilidades"""
        try:
            conn = self._get_conn()
            cursor = conn.cursor()
            
            # Buscar todas as peças do carro com durabilidade
            cursor.execute('''
                SELECT p.id, p.peca_loja_id, p.nome, p.tipo, p.durabilidade_maxima, p.durabilidade_atual, pl.compatibilidade
                FROM pecas p
                LEFT JOIN pecas_loja pl ON p.peca_loja_id = pl.id
                WHERE p.carro_id = %s AND p.instalado = 1
                ORDER BY p.tipo
            ''', (carro_id,))
            
            rows = cursor.fetchall()
            conn.close()
            
            pecas_com_compat = []
            for row in rows:
                peca_id, peca_loja_id, nome, tipo_peca, durabilidade_maxima, durabilidade_atual, compatibilidade_json = row
                
                # Processar compatibilidade
                compatibilidades = []
                if compatibilidade_json:
                    try:
                        if isinstance(compatibilidade_json, str):
                            if compatibilidade_json.startswith('{'):
                                compat_data = json.loads(compatibilidade_json)
                                compatibilidades = compat_data.get('compatibilidades', [])
                            else:
                                # String antiga, fazer split
                                if compatibilidade_json.lower() != 'universal':
                                    compatibilidades = [item.strip() for item in compatibilidade_json.split(',')]
                        elif isinstance(compatibilidade_json, dict):
                            compatibilidades = compatibilidade_json.get('compatibilidades', [])
                    except:
                        compatibilidades = []
                
                # Se a compatibilidade é universal, retornar array vazio
                # Isso padroniza: vazio = universal, preenchido = específico
                if compatibilidades and all(str(c).lower() == 'universal' for c in compatibilidades):
                    compatibilidades = []
                
                pecas_com_compat.append({
                    'id': peca_id,
                    'peca_loja_id': peca_loja_id,
                    'nome': nome,
                    'tipo': tipo_peca,
                    'durabilidade_maxima': durabilidade_maxima or 100,
                    'durabilidade_atual': durabilidade_atual or 100,
                    'compatibilidades': compatibilidades  # Array de IDs de carros compatíveis (vazio = universal)
                })
            
            return pecas_com_compat
        except Exception as e:
            print(f"Erro ao obter peças com compatibilidade: {e}")
            import traceback
            traceback.print_exc()
            return []

    def obter_peca_instalada_por_tipo(self, carro_id, tipo_peca):
        """Obtém a peça instalada de um tipo específico no carro (ou None se não houver)"""
        try:
            conn = self._get_conn()
            cursor = conn.cursor()
            cursor.execute('''
                SELECT * FROM pecas 
                WHERE carro_id = %s AND tipo = %s AND instalado = 1
                LIMIT 1
            ''', (carro_id, tipo_peca))
            
            row = cursor.fetchone()
            conn.close()
            
            if row:
                return {
                    'id': row[0],
                    'carro_id': row[1],
                    'nome': row[2],
                    'tipo': row[3],
                    'durabilidade_maxima': row[4],
                    'durabilidade_atual': row[5],
                    'preco': row[6],
                    'coeficiente_quebra': row[7],
                    'instalado': row[8],
                    'data_criacao': row[9] if len(row) > 9 else None
                }
            return None
        except Exception as e:
            print(f"Erro ao obter peça instalada: {e}")
            return None

    def validar_compatibilidade_peca_carro(self, peca_id, carro_id):
        """Valida se uma peça é compatível com um carro"""
        try:
            conn = self._get_conn()
            cursor = conn.cursor()
            
            # Obter compatibilidade da peça
            cursor.execute('''
                SELECT compatibilidade FROM pecas_loja WHERE id = %s
            ''', (peca_id,))
            peca_row = cursor.fetchone()
            if not peca_row:
                conn.close()
                return False, "Peça não encontrada"
            
            compatibilidade_str = peca_row[0] or '{"compatibilidades": ["universal"]}'
            
            # Converter para JSON se estiver em string
            try:
                # Tentar parsear como JSON
                if isinstance(compatibilidade_str, str) and compatibilidade_str.startswith('{'):
                    compatibilidade_data = json.loads(compatibilidade_str)
                    compatibilidades = compatibilidade_data.get('compatibilidades', ['universal'])
                else:
                    # Compatibilidade antiga em string, converter
                    if compatibilidade_str.lower() == 'universal':
                        compatibilidades = ['universal']
                    else:
                        # Separar por vírgula ou pipe
                        items = []
                        for item in compatibilidade_str.split(','):
                            item = item.strip()
                            if item:
                                items.append(item)
                        compatibilidades = items if items else ['universal']
            except:
                compatibilidades = ['universal']
            
            # Se for universal, sempre compatível
            if 'universal' in [c.lower() for c in compatibilidades]:
                conn.close()
                return True, "Compatível"
            
            # Obter modelo do carro
            cursor.execute('''
                SELECT modelo_id, marca FROM carros WHERE id = %s
            ''', (carro_id,))
            carro_row = cursor.fetchone()
            if not carro_row:
                conn.close()
                return False, "Carro não encontrado"
            
            modelo_carro = carro_row[0]
            
            # Se o modelo está na lista de compatibilidade
            compatibilidades_lower = [c.lower() for c in compatibilidades]
            if modelo_carro and modelo_carro.lower() in compatibilidades_lower:
                conn.close()
                return True, "Compatível"
            
            conn.close()
            return False, f"Peça não é compatível com este modelo"
            
        except Exception as e:
            print(f"Erro ao validar compatibilidade: {e}")
            traceback.print_exc()
            return False, f"Erro ao validar: {str(e)}"

    def criar_peca_armazem(self, peca_loja_id, equipe_id=None):
        """Cria uma peça no armazém (tabela pecas) a partir de uma peça_loja_id"""
        try:
            conn = self._get_conn()
            cursor = conn.cursor()
            
            # Verificar se a peça já existe no armazém para essa equipe
            cursor.execute('''
                SELECT id FROM pecas 
                WHERE peca_loja_id = %s AND instalado = 0 AND carro_id IS NULL AND equipe_id = %s
                LIMIT 1
            ''', (peca_loja_id, equipe_id))
            
            resultado = cursor.fetchone()
            
            if resultado:
                # Peça já existe no armazém
                conn.close()
                print(f"[ARMAZÉM] Peça {peca_loja_id} já existe no armazém para equipe {equipe_id}")
                return resultado[0]
            
            # Peça não existe, criar nova
            import uuid
            nova_peca_id = str(uuid.uuid4())
            
            # Buscar dados da peça_loja
            cursor.execute('SELECT nome, tipo, preco FROM pecas_loja WHERE id = %s', (peca_loja_id,))
            peca_loja = cursor.fetchone()
            
            if not peca_loja:
                conn.close()
                print(f"[ARMAZÉM] ERRO: Peça loja {peca_loja_id} não encontrada")
                return None
            
            nome, tipo, preco = peca_loja
            
            # Inserir peça no armazém COM equipe_id
            cursor.execute('''
                INSERT INTO pecas 
                (id, peca_loja_id, nome, tipo, preco, durabilidade_maxima, durabilidade_atual, instalado, carro_id, equipe_id, data_criacao)
                VALUES (%s, %s, %s, %s, %s, 100, 100, 0, NULL, %s, NOW())
            ''', (nova_peca_id, peca_loja_id, nome, tipo, preco, equipe_id))
            
            conn.commit()
            conn.close()
            
            print(f"[ARMAZÉM] Peça criada no armazém: {nova_peca_id} ({nome}) para equipe {equipe_id}")
            return nova_peca_id
        except Exception as e:
            print(f"Erro ao criar peça no armazém: {e}")
            import traceback
            traceback.print_exc()
            return None

    def instalar_peca_no_carro(self, peca_id, carro_id):
        """Instala uma peça no carro, removendo a anterior se existir (com validação de limite e compatibilidade)"""
        try:
            conn = self._get_conn()
            cursor = conn.cursor()
            
            # 0. Validar compatibilidade ANTES de fazer qualquer coisa
            compativel, msg = self.validar_compatibilidade_peca_carro(peca_id, carro_id)
            if not compativel:
                print(f"[INSTALAR] ERRO: {msg}")
                return False, msg
            
            # 1. Obter dados da peça a ser instalada
            cursor.execute('SELECT * FROM pecas_loja WHERE id = %s', (peca_id,))
            peca_loja_row = cursor.fetchone()
            if not peca_loja_row:
                print(f"[INSTALAR] ERRO: Peça {peca_id} não encontrada")
                return False, "Peça não encontrada"
            
            tipo_peca = peca_loja_row[2]  # tipo está na posição 2
            
            # 2. Verificar e remover peça antiga do mesmo tipo ANTES de validar limite
            peca_antiga = self.obter_peca_instalada_por_tipo(carro_id, tipo_peca)
            
            if peca_antiga:
                # Desinstalar peça antiga: instalado = 0 e carro_id = NULL (vai pro armazém)
                print(f"[INSTALAR] Desinstalando peça antiga: {peca_antiga['nome']} (ID: {peca_antiga['id']})")
                cursor.execute('''
                    UPDATE pecas 
                    SET instalado = 0, carro_id = NULL
                    WHERE id = %s
                ''', (peca_antiga['id'],))
                conn.commit()  # Commit da desinstalação para que validar_limite veja a mudança
            
            # 3. Validar limite (agora com a peça antiga já removida)
            if not self.validar_limite_peca(carro_id, tipo_peca):
                conn.close()
                return False, f"Você já possui uma {tipo_peca} instalada. Máximo permitido: 1 por carro"
            
            # 4. PROCURAR PEÇA DO ARMAZÉM COM A MESMA peca_loja_id
            # A peça já existe no armazém se alguém já comprou antes
            cursor.execute('''
                SELECT id FROM pecas 
                WHERE peca_loja_id = %s AND instalado = 0 AND carro_id IS NULL
                LIMIT 1
            ''', (peca_id,))
            
            peca_armazem_row = cursor.fetchone()
            
            if not peca_armazem_row:
                # Peça NÃO existe no armazém - não pode instalar sem comprar primeiro!
                conn.close()
                print(f"[INSTALAR] ❌ ERRO: Peça {peca_id} não encontrada no armazém. Compre a peça primeiro!")
                return False, "Peça não está disponível no armazém. Você precisa comprar a peça primeiro!"
            
            # Usar a peça que já existe no armazém
            peca_nova_id = peca_armazem_row[0]
            print(f"[INSTALAR] ✓ Usando peça existente do armazém: {peca_nova_id}")
            
            # Obter equipe_id do carro para manter na peça instalada
            cursor.execute('SELECT equipe_id FROM carros WHERE id = %s', (carro_id,))
            carro_row = cursor.fetchone()
            equipe_id_carro = carro_row[0] if carro_row else None
            
            cursor.execute('''
                UPDATE pecas 
                SET carro_id = %s, instalado = 1, equipe_id = %s
                WHERE id = %s
            ''', (carro_id, equipe_id_carro, peca_nova_id))
            
            # NOTA: Não precisamos mais atualizar as colunas motor_id, cambio_id, etc. em carros
            # A tabela pecas é agora a única fonte de verdade para relacionamentos de peças!
            
            conn.commit()
            conn.close()
            
            print(f"[INSTALAR] ✅ Peça {tipo_peca} instalada com sucesso no carro {carro_id}")
            return True, "Peça instalada com sucesso!"
            
        except Exception as e:
            print(f"Erro ao instalar peça: {e}")
            import traceback
            traceback.print_exc()
            return False, f"Erro ao instalar peça: {str(e)}"

    def adicionar_peca_armazem(self, equipe_id, peca_loja_id, nome, tipo, durabilidade, preco, coeficiente_quebra):
        """Adiciona uma peça ao armazém da equipe (sem carro, instalado = 0)"""
        try:
            import uuid
            
            conn = self._get_conn()
            cursor = conn.cursor()
            
            # Desabilitar temporariamente a foreign key constraint
            cursor.execute('SET FOREIGN_KEY_CHECKS=0')
            
            peca_id = str(uuid.uuid4())
            
            print(f"[DB ARMAZÉM] Adicionando peça ao armazém:")
            print(f"  - ID: {peca_id}")
            print(f"  - Peça Loja: {peca_loja_id}")
            print(f"  - Nome: {nome}")
            print(f"  - Tipo: {tipo}")
            print(f"  - Durabilidade: {durabilidade}")
            print(f"  - Preço: {preco}")
            print(f"  - Coeficiente Quebra: {coeficiente_quebra}")
            
            cursor.execute('''
                INSERT INTO pecas 
                (id, carro_id, equipe_id, peca_loja_id, nome, tipo, durabilidade_maxima, durabilidade_atual, preco, coeficiente_quebra, instalado)
                VALUES (%s, NULL, %s, %s, %s, %s, %s, %s, %s, %s, 0)
            ''', (peca_id, equipe_id, peca_loja_id, nome, tipo, durabilidade, durabilidade, preco, coeficiente_quebra))
            
            conn.commit()
            
            # Reabilitar foreign key constraint
            cursor.execute('SET FOREIGN_KEY_CHECKS=1')
            
            # Verificar se foi inserido
            cursor.execute('SELECT id FROM pecas WHERE id = %s', (peca_id,))
            result = cursor.fetchone()
            conn.close()
            
            if result:
                print(f"[DB ARMAZÉM] ✅ Peça adicionada ao armazém com sucesso!")
                return True
            else:
                print(f"[DB ARMAZÉM] ❌ ERRO: Peça não foi encontrada após salvar!")
                return False
                
        except Exception as e:
            print(f"[DB ARMAZÉM] ❌ Erro ao adicionar peça ao armazém: {e}")
            import traceback
            traceback.print_exc()
            return False

    def adicionar_peca_carro(self, equipe_id, carro_id, peca_loja_id, nome, tipo, durabilidade, preco, coeficiente_quebra, pix_id=None):
        """Adiciona uma peça diretamente instalada no carro (instalado = 1, para compras com PIX)"""
        try:
            import uuid
            
            conn = self._get_conn()
            cursor = conn.cursor()
            
            # Desabilitar temporariamente a foreign key constraint
            cursor.execute('SET FOREIGN_KEY_CHECKS=0')
            
            peca_id = str(uuid.uuid4())
            
            print(f"[DB CARRO] Adicionando peça ao carro:")
            print(f"  - ID: {peca_id}")
            print(f"  - Carro: {carro_id}")
            print(f"  - Peça Loja: {peca_loja_id}")
            print(f"  - Nome: {nome}")
            print(f"  - Tipo: {tipo}")
            print(f"  - Durabilidade: {durabilidade}")
            print(f"  - Preço: {preco}")
            print(f"  - Coeficiente Quebra: {coeficiente_quebra}")
            if pix_id:
                print(f"  - PIX ID: {pix_id}")
            
            cursor.execute('''
                INSERT INTO pecas 
                (id, carro_id, equipe_id, peca_loja_id, nome, tipo, durabilidade_maxima, durabilidade_atual, preco, coeficiente_quebra, instalado, pix_id)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 1, %s)
            ''', (peca_id, carro_id, equipe_id, peca_loja_id, nome, tipo, durabilidade, durabilidade, preco, coeficiente_quebra, pix_id))
            
            conn.commit()
            
            # Reabilitar foreign key constraint
            cursor.execute('SET FOREIGN_KEY_CHECKS=1')
            
            # Verificar se foi inserido
            cursor.execute('SELECT id FROM pecas WHERE id = %s', (peca_id,))
            result = cursor.fetchone()
            conn.close()
            
            if result:
                print(f"[DB CARRO] ✅ Peça adicionada ao carro com sucesso!")
                return True
            else:
                print(f"[DB CARRO] ❌ ERRO: Peça não foi encontrada após salvar!")
                return False
                
        except Exception as e:
            print(f"[DB CARRO] ❌ Erro ao adicionar peça ao carro: {e}")
            import traceback
            traceback.print_exc()
            return False

            print(f"[DB] Salvando solicitação de peça:")
            print(f"  - ID: {id}")
            print(f"  - Equipe: {equipe_id}")
            print(f"  - Peça: {peca_id}")
            print(f"  - Quantidade: {quantidade}")
            print(f"  - Status: {status}")
            print(f"  - Carro: {carro_id}")
            
            conn = self._get_conn()
            cursor = conn.cursor()

            cursor.execute('''
                INSERT INTO solicitacoes_pecas 
                (id, equipe_id, peca_id, carro_id, quantidade, status, data_solicitacao)
                VALUES (%s, %s, %s, %s, %s, %s, NOW())
                ON DUPLICATE KEY UPDATE
                peca_id = VALUES(peca_id),
                carro_id = VALUES(carro_id),
                quantidade = VALUES(quantidade),
                status = VALUES(status),
                data_atualizacao = NOW()
            ''', (id, equipe_id, peca_id, carro_id, quantidade, status))

            conn.commit()
            
            # Verificar se foi inserido
            cursor.execute('SELECT id FROM solicitacoes_pecas WHERE id = %s', (id,))
            result = cursor.fetchone()
            conn.close()
            
            if result:
                print(f"[DB] ✅ Solicitação salva com sucesso!")
                return True
            else:
                print(f"[DB] ❌ ERRO: Solicitação não foi encontrada após salvar!")
                return False
                
        except Exception as e:
            print(f"[DB] ❌ Erro ao salvar solicitação de peça: {e}")
            import traceback
            traceback.print_exc()
            return False

    def instalar_peca_warehouse(self, peca_loja_id: str, carro_id: str, equipe_id: str) -> bool:
        """Instala uma peça do armazém no carro - remove antigas do mesmo tipo primeiro"""
        try:
            cursor = self.db.cursor()
            
            # Primeiro, obter o tipo da peça da pecas_loja
            print(f"\n[WAREHOUSE] ===== INICIANDO INSTALAÇÃO =====")
            print(f"[WAREHOUSE] Peca Loja ID: {peca_loja_id}")
            print(f"[WAREHOUSE] Carro ID: {carro_id}")
            print(f"[WAREHOUSE] Equipe ID: {equipe_id}")
            
            cursor.execute('''
                SELECT tipo, nome FROM pecas_loja WHERE id = %s
            ''', (str(peca_loja_id),))
            
            resultado = cursor.fetchone()
            if not resultado:
                print(f"[WAREHOUSE] ❌ Peça loja {peca_loja_id} não encontrada em pecas_loja")
                return False
            
            tipo_peca, nome_peca_loja = resultado
            print(f"[WAREHOUSE] ✅ Peça Loja encontrada: {nome_peca_loja} (tipo: {tipo_peca})")
            
            # Buscar TODAS as peças instaladas neste carro para debug
            cursor.execute('''
                SELECT id, nome, tipo, carro_id, instalado FROM pecas 
                WHERE carro_id = %s AND equipe_id = %s
            ''', (str(carro_id), str(equipe_id)))
            
            todas_pecas = cursor.fetchall()
            print(f"[WAREHOUSE] Peças atuais no carro {carro_id}:")
            for pid, pnome, ptipo, pcarroid, pinstalado in todas_pecas:
                print(f"  - {pnome} (tipo: {ptipo}, instalado: {pinstalado})")
            
            # ANTES DE INSTALAR: Remover TODAS as peças antigas do mesmo tipo
            print(f"\n[WAREHOUSE] 🗑️ Procurando peças do tipo '{tipo_peca}' para remover...")
            cursor.execute('''
                SELECT id, nome, tipo FROM pecas 
                WHERE carro_id = %s AND tipo = %s AND instalado = 1 AND equipe_id = %s
            ''', (str(carro_id), tipo_peca, str(equipe_id)))
            
            pecas_antigas = cursor.fetchall()
            print(f"[WAREHOUSE] Encontradas {len(pecas_antigas)} peça(s) do tipo {tipo_peca}")
            
            # Remover TODAS as peças antigas
            for peca_id, peca_nome, peca_tipo_check in pecas_antigas:
                print(f"[WAREHOUSE] 🗑️ Removendo: {peca_nome} (ID: {peca_id}, tipo: {peca_tipo_check})")
                cursor.execute('''
                    UPDATE pecas 
                    SET carro_id = NULL, instalado = 0, pix_id = NULL
                    WHERE id = %s
                ''', (str(peca_id),))
            
            self.db.commit()
            print(f"[WAREHOUSE] ✅ {len(pecas_antigas)} peça(s) desinstalada(s)")
            
            # Agora instalar a peça NOVA
            print(f"\n[WAREHOUSE] 📦 Instalando peça nova: {nome_peca_loja}")
            cursor.execute('''
                UPDATE pecas 
                SET instalado = 1, carro_id = %s
                WHERE peca_loja_id = %s AND equipe_id = %s AND instalado = 0
            ''', (str(carro_id), str(peca_loja_id), str(equipe_id)))
            
            linhas_afetadas = cursor.rowcount
            print(f"[WAREHOUSE] Linhas afetadas na UPDATE: {linhas_afetadas}")
            
            if linhas_afetadas > 0:
                # Determinar qual coluna atualizar baseado no tipo da peça
                campo_carro = None
                if tipo_peca.lower() == 'motor':
                    campo_carro = 'motor_id'
                elif tipo_peca.lower() == 'cambio':
                    campo_carro = 'cambio_id'
                elif tipo_peca.lower() == 'suspensao':
                    campo_carro = 'suspensao_id'
                elif tipo_peca.lower() == 'kit_angulo':
                    campo_carro = 'kit_angulo_id'
                elif tipo_peca.lower() == 'diferencial':
                    campo_carro = 'diferencial_id'
                
                if campo_carro:
                    # Atualizar o carro com o ID da peça
                    sql_update = f'''
                        UPDATE carros 
                        SET {campo_carro} = %s
                        WHERE id = %s AND equipe_id = %s
                    '''
                    print(f"[WAREHOUSE] Atualizando coluna {campo_carro} do carro")
                    cursor.execute(sql_update, (str(peca_loja_id), str(carro_id), str(equipe_id)))
                    
                    self.db.commit()
                    print(f"[WAREHOUSE] ✅ Peça {nome_peca_loja} instalada com sucesso!")
                    print(f"[WAREHOUSE] ===== INSTALAÇÃO CONCLUÍDA =====\n")
                    return True
                else:
                    self.db.commit()
                    print(f"[WAREHOUSE] ⚠️ Tipo '{tipo_peca}' não mapeado para coluna")
                    print(f"[WAREHOUSE] ===== INSTALAÇÃO CONCLUÍDA (COM AVISO) =====\n")
                    return True
            else:
                print(f"[WAREHOUSE] ❌ Nenhuma linha afetada! Peça pode não existir ou estar em outro estado")
                print(f"[WAREHOUSE] Procurando a peça para debug...")
                
                cursor.execute('''
                    SELECT id, instalado, carro_id, pix_id FROM pecas 
                    WHERE peca_loja_id = %s AND equipe_id = %s
                ''', (str(peca_loja_id), str(equipe_id)))
                
                peca_info = cursor.fetchone()
                if peca_info:
                    pid, pinstalado, pcarroid, ppixid = peca_info
                    print(f"[WAREHOUSE] Peça encontrada: ID={pid}, instalado={pinstalado}, carro_id={pcarroid}, pix_id={ppixid}")
                else:
                    print(f"[WAREHOUSE] ❌ Peça não encontrada no banco!")
                
                self.db.commit()
                print(f"[WAREHOUSE] ===== INSTALAÇÃO FALHOU =====\n")
                return False
                
        except Exception as e:
            print(f"[WAREHOUSE] ❌ ERRO: {e}")
            import traceback
            traceback.print_exc()
            self.db.rollback()
            print(f"[WAREHOUSE] ===== ERRO FATALL =====\n")
            return False
            return False

    def salvar_solicitacao_carro(self, id_solicitacao, equipe_id, tipo_carro, status, data_solicitacao):
        """Salva uma solicitação de carro no banco de dados. tipo_carro é formato 'UUID|Marca|Modelo' ou UUID (legacy)"""
        try:
            conn = self._get_conn()
            cursor = conn.cursor()

            cursor.execute('''
                INSERT INTO solicitacoes_carros 
                (id, equipe_id, tipo_carro, status, data_solicitacao, data_atualizacao)
                VALUES (%s, %s, %s, %s, %s, NOW())
                ON DUPLICATE KEY UPDATE
                tipo_carro = VALUES(tipo_carro),
                status = VALUES(status),
                data_atualizacao = NOW()
            ''', (id_solicitacao, equipe_id, tipo_carro, status, data_solicitacao))

            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"Erro ao salvar solicitação de carro: {e}")
            return False

    def criar_solicitacao_ativacao_carro(self, equipe_id: str, carro_id: str, carro_anterior_id: str = None) -> str:
        """Cria uma solicitação de ativação de carro (pendente). Retorna o id da solicitação."""
        import uuid as _uuid
        try:
            conn = self._get_conn()
            cursor = conn.cursor()
            cursor.execute('SELECT marca, modelo FROM carros WHERE id = %s AND equipe_id = %s', (carro_id, equipe_id))
            row = cursor.fetchone()
            marca = (row[0] or 'Carro') if row else 'Carro'
            modelo = (row[1] or 'Ativação') if row else 'Ativação'
            tipo_carro = f"{carro_id}|{marca}|{modelo}"
            sol_id = str(_uuid.uuid4())
            if self._column_exists('solicitacoes_carros', 'tipo_solicitacao'):
                cursor.execute('''
                    INSERT INTO solicitacoes_carros
                    (id, equipe_id, carro_id, carro_anterior_id, tipo_carro, tipo_solicitacao, status)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                ''', (sol_id, equipe_id, carro_id, carro_anterior_id, tipo_carro, 'ativacao', 'pendente'))
            else:
                cursor.execute('''
                    INSERT INTO solicitacoes_carros
                    (id, equipe_id, tipo_carro, status, data_solicitacao, data_atualizacao)
                    VALUES (%s, %s, %s, %s, NOW(), NOW())
                ''', (sol_id, equipe_id, tipo_carro, 'pendente'))
            conn.commit()
            conn.close()
            return sol_id
        except Exception as e:
            print(f"Erro ao criar solicitação de ativação: {e}")
            import traceback
            traceback.print_exc()
            return None

    def salvar_solicitacao_peca(self, id, equipe_id, peca_id, quantidade, status, carro_id=None):
        """Salva uma solicitação de peça no banco de dados"""
        try:
            conn = self._get_conn()
            cursor = conn.cursor()

            cursor.execute('''
                INSERT INTO solicitacoes_pecas 
                (id, equipe_id, peca_id, carro_id, quantidade, status, data_solicitacao, data_atualizacao)
                VALUES (%s, %s, %s, %s, %s, %s, NOW(), NOW())
                ON DUPLICATE KEY UPDATE
                quantidade = VALUES(quantidade),
                status = VALUES(status),
                carro_id = VALUES(carro_id),
                data_atualizacao = NOW()
            ''', (id, equipe_id, peca_id, carro_id, quantidade, status))

            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"Erro ao salvar solicitação de peça: {e}")
            import traceback
            traceback.print_exc()
            return False

    def carregar_solicitacoes_pecas(self, equipe_id=None):
        """Carrega solicitações de peças do banco de dados com dados enriquecidos"""
        try:
            conn = self._get_conn()
            cursor = conn.cursor()

            # Query com JOINs; usar sp.tipo_peca como fallback quando p.tipo for NULL
            cols = [
                'sp.id', 'sp.equipe_id', 'sp.peca_id', 'sp.carro_id', 'sp.quantidade', 'sp.status',
                'sp.data_solicitacao', 'sp.data_atualizacao',
                'e.nome as equipe_nome', 'p.nome as peca_nome', 'p.tipo as peca_tipo_join', 'p.preco',
                'c.marca as carro_marca', 'c.modelo as carro_modelo', 'c.status as carro_status'
            ]
            if self._column_exists('solicitacoes_pecas', 'tipo_peca'):
                cols.insert(cols.index('p.preco'), 'sp.tipo_peca')
            # Ocultar solicitações aprovadas (instalado) com mais de 72h
            filtro_72h = " (sp.status != 'instalado' OR sp.data_atualizacao >= NOW() - INTERVAL 72 HOUR) "
            query = '''
                SELECT ''' + ', '.join(cols) + '''
                FROM solicitacoes_pecas sp
                LEFT JOIN equipes e ON sp.equipe_id = e.id
                LEFT JOIN pecas_loja p ON sp.peca_id = p.id
                LEFT JOIN carros c ON sp.carro_id = c.id
                WHERE ''' + filtro_72h
            if equipe_id:
                query += ' AND sp.equipe_id = %s'
                cursor.execute(query + ' ORDER BY sp.data_solicitacao DESC', (equipe_id,))
            else:
                cursor.execute(query + ' ORDER BY sp.data_solicitacao DESC')

            rows = cursor.fetchall()
            conn.close()

            has_tipo_peca_col = self._column_exists('solicitacoes_pecas', 'tipo_peca')
            solicitacoes = []
            for row in rows:
                # Índices: 0 id, 1 equipe_id, 2 peca_id, 3 carro_id, 4 quantidade, 5 status, 6 data_sol, 7 data_atual
                # 8 equipe_nome, 9 peca_nome, 10 peca_tipo_join, [11 tipo_peca se existe], 11 ou 12 preco, depois carro
                if has_tipo_peca_col:
                    peca_tipo_join, tipo_peca_tab, preco = row[10], row[11], row[12]
                    carro_marca, carro_modelo, carro_status = row[13], row[14], row[15]
                else:
                    peca_tipo_join, tipo_peca_tab, preco = row[10], None, row[11]
                    carro_marca, carro_modelo, carro_status = row[12], row[13], row[14]
                carro = None
                if carro_marca and carro_modelo:
                    carro = {'marca': carro_marca, 'modelo': carro_modelo, 'status': carro_status}
                solicitacao = {
                    'id': row[0],
                    'equipe_id': row[1],
                    'peca_id': row[2],
                    'carro_id': row[3],
                    'quantidade': row[4],
                    'status': row[5],
                    'data_solicitacao': row[6].isoformat() if row[6] else None,
                    'data_atualizacao': row[7].isoformat() if row[7] else None,
                    'equipe_nome': row[8],
                    'peca_nome': row[9] or '',
                    'peca_tipo': (peca_tipo_join or tipo_peca_tab) or '',
                    'preco': float(preco) if preco else 0.0,
                    'carro': carro
                }
                solicitacoes.append(solicitacao)

            return solicitacoes
        except Exception as e:
            print(f"Erro ao carregar solicitações de peças: {e}")
            import traceback
            traceback.print_exc()
            return []

    def carregar_solicitacoes_carros(self, equipe_id=None):
        """Carrega solicitações de carros do banco de dados com dados completos do carro"""
        try:
            conn = self._get_conn()
            cursor = conn.cursor()

            # Ocultar solicitações aprovadas com mais de 72h
            filtro_72h = " (sc.status NOT IN ('aprovado', 'aprovada') OR sc.data_atualizacao >= NOW() - INTERVAL 72 HOUR) "
            query = '''
                SELECT
                    sc.id, sc.equipe_id, sc.tipo_carro, sc.status, sc.data_solicitacao, sc.data_atualizacao,
                    e.nome as equipe_nome, sc.carro_id, sc.carro_anterior_id, sc.tipo_solicitacao
                FROM solicitacoes_carros sc
                LEFT JOIN equipes e ON sc.equipe_id = e.id
                WHERE ''' + filtro_72h
            if equipe_id:
                query += ' AND sc.equipe_id = %s'
                cursor.execute(query + ' ORDER BY sc.data_solicitacao DESC', (equipe_id,))
            else:
                cursor.execute(query + ' ORDER BY sc.data_solicitacao DESC')

            rows = cursor.fetchall()
            conn.close()

            solicitacoes = []
            for row in rows:
                solicitacao = {
                    'id': row[0],
                    'equipe_id': row[1],
                    'tipo_carro': row[2],
                    'status': row[3],
                    'data_solicitacao': row[4].isoformat() if row[4] else None,
                    'data_atualizacao': row[5].isoformat() if row[5] else None,
                    'equipe_nome': row[6] or 'Desconhecida',
                    'timestamp': row[4].isoformat() if row[4] else None,
                    'carro_id': row[7],
                    'carro_anterior_id': row[8],
                    'tipo_solicitacao': row[9]
                }
                
                # Determinar qual carro carregar baseado no tipo de solicitação
                carro_uuid = None
                
                if solicitacao['tipo_solicitacao'] == 'ativacao':
                    # Para ativação, usar carro_id diretamente
                    carro_uuid = solicitacao['carro_id']
                else:
                    # Para outros tipos, extrair do tipo_carro (formato: "UUID|marca|modelo")
                    tipo_partes = solicitacao['tipo_carro'].split('|') if solicitacao['tipo_carro'] else []
                    if len(tipo_partes) >= 1:
                        carro_uuid = tipo_partes[0]
                
                if carro_uuid:
                    # Carregar a equipe completa para obter os dados do carro
                    equipe_completa = self.carregar_equipe(solicitacao['equipe_id'])
                    if equipe_completa:
                        # Procurar o carro na equipe
                        for carro in equipe_completa.carros:
                            if str(carro.id) == str(carro_uuid):
                                # Preencher dados do carro
                                solicitacao['numero_carro'] = carro.numero_carro
                                solicitacao['marca'] = carro.marca
                                solicitacao['modelo'] = carro.modelo
                                if carro.motor and carro.cambio and carro.kit_angulo and carro.suspensao:
                                    solicitacao['condicao'] = (carro.motor.durabilidade_atual + carro.cambio.durabilidade_atual + 
                                                              carro.kit_angulo.durabilidade_atual + carro.suspensao.durabilidade_atual) / 4
                                else:
                                    solicitacao['condicao'] = 0
                                solicitacao['batidas_totais'] = carro.batidas_totais
                                solicitacao['vitoria'] = carro.vitoria
                                solicitacao['derrotas'] = carro.derrotas
                                solicitacao['empates'] = carro.empates
                                
                                # Preencher nomes das peças
                                solicitacao['motor_nome'] = carro.motor.nome if carro.motor else None
                                solicitacao['cambio_nome'] = carro.cambio.nome if carro.cambio else None
                                solicitacao['suspensao_nome'] = carro.suspensao.nome if carro.suspensao else None
                                solicitacao['kit_angulo_nome'] = carro.kit_angulo.nome if carro.kit_angulo else None
                                solicitacao['diferencial_nome'] = carro.diferenciais[0].nome if carro.diferenciais else None
                                break
                
                solicitacoes.append(solicitacao)

            return solicitacoes
        except Exception as e:
            print(f"Erro ao carregar solicitações de carros: {e}")
            import traceback
            traceback.print_exc()
            return []

    def atualizar_status_solicitacao_peca(self, solicitacao_id, novo_status):
        """Atualiza o status de uma solicitação de peça"""
        try:
            conn = self._get_conn()
            cursor = conn.cursor()

            cursor.execute('''
                UPDATE solicitacoes_pecas 
                SET status = %s, data_atualizacao = NOW() 
                WHERE id = %s
            ''', (novo_status, solicitacao_id))

            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"Erro ao atualizar status da solicitação de peça: {e}")
            return False

    def atualizar_carro_id_solicitacao_peca(self, solicitacao_id, carro_id):
        """Atualiza o carro_id de uma solicitação de peça"""
        try:
            print(f"\n[DB UPDATE] ========== INICIANDO UPDATE ==========")
            print(f"[DB UPDATE] solicitacao_id = {solicitacao_id}")
            print(f"[DB UPDATE] carro_id = {carro_id}")
            print(f"[DB UPDATE] carro_id é None? {carro_id is None}")
            print(f"[DB UPDATE] carro_id é vazio? {carro_id == ''}")
            
            conn = self._get_conn()
            cursor = conn.cursor()

            sql = '''
                UPDATE solicitacoes_pecas 
                SET carro_id = %s, data_atualizacao = NOW() 
                WHERE id = %s
            '''
            
            print(f"[DB UPDATE] SQL: {sql}")
            print(f"[DB UPDATE] Parametros: carro_id={carro_id}, solicitacao_id={solicitacao_id}")
            
            cursor.execute(sql, (carro_id, solicitacao_id))
            
            print(f"[DB UPDATE] Rows affected: {cursor.rowcount}")
            print(f"[DB UPDATE] Last Insert ID: {cursor.lastrowid}")
            
            conn.commit()
            
            # Verificar se foi atualizado
            cursor.execute('SELECT carro_id FROM solicitacoes_pecas WHERE id = %s', (solicitacao_id,))
            result = cursor.fetchone()
            print(f"[DB UPDATE] Após UPDATE, carro_id no banco = {result[0] if result else 'NÃO ENCONTRADO'}")
            
            conn.close()
            
            print(f"[DB UPDATE] ========== UPDATE CONCLUÍDO ==========\n")
            return True
        except Exception as e:
            print(f"[DB UPDATE] ❌ ERRO: {e}")
            import traceback
            traceback.print_exc()
            return False

    def atualizar_status_solicitacao_carro(self, solicitacao_id, novo_status):
        """Atualiza o status de uma solicitação de carro"""
        try:
            conn = self._get_conn()
            cursor = conn.cursor()
            
            # Garantir que a coluna carro_id existe na tabela equipes
            try:
                cursor.execute('ALTER TABLE equipes ADD COLUMN carro_id TEXT')
                conn.commit()
            except:
                pass  # A coluna provavelmente já existe

            # Se o status for 'aprovado' ou 'ativo', processar a mudança/criação
            if novo_status == 'aprovado':
                # Primeiro, obter os dados da solicitação
                cursor.execute('''
                    SELECT sc.equipe_id, sc.tipo_carro, sc.tipo_solicitacao, sc.carro_id, sc.carro_anterior_id
                    FROM solicitacoes_carros sc
                    WHERE sc.id = %s
                ''', (solicitacao_id,))
                
                row = cursor.fetchone()
                if not row:
                    print(f"Solicitação {solicitacao_id} não encontrada")
                    conn.close()
                    return False
                
                equipe_id, tipo_carro, tipo_solicitacao, carro_id_novo, carro_anterior_id = row
                
                # Se for solicitação de ATIVAÇÃO, usar a nova lógica
                if tipo_solicitacao == 'ativacao':
                    print(f"[ATIVAÇÃO CARRO] Processando aprovação de ativação para equipe {equipe_id}")
                    print(f"[ATIVAÇÃO CARRO]   Carro novo: {carro_id_novo}")
                    print(f"[ATIVAÇÃO CARRO]   Carro anterior: {carro_anterior_id}")
                    
                    # Verificar se o carro novo existe
                    cursor.execute('SELECT id FROM carros WHERE id = %s AND equipe_id = %s', (carro_id_novo, equipe_id))
                    carro_novo_existe = cursor.fetchone()
                    
                    if not carro_novo_existe:
                        print(f"[ERRO] Carro {carro_id_novo} não encontrado para equipe {equipe_id}")
                        conn.close()
                        return False
                    
                    # Colocar carro anterior em repouso (se existir)
                    if carro_anterior_id:
                        cursor.execute('''
                            UPDATE carros 
                            SET status = 'repouso', timestamp_repouso = NOW() 
                            WHERE id = %s
                        ''', (carro_anterior_id,))
                        print(f"[ATIVAÇÃO CARRO] Carro anterior {carro_anterior_id} colocado em repouso")
                    
                    # Ativar o novo carro
                    cursor.execute('''
                        UPDATE carros 
                        SET status = 'ativo', timestamp_ativo = NOW() 
                        WHERE id = %s
                    ''', (carro_id_novo,))
                    print(f"[ATIVAÇÃO CARRO] Carro novo {carro_id_novo} ativado")
                    
                    # Atualizar a equipe para usar o novo carro
                    cursor.execute('UPDATE equipes SET carro_id = %s WHERE id = %s', (carro_id_novo, equipe_id))
                    print(f"[ATIVAÇÃO CARRO] Equipe {equipe_id} atualizada para usar carro {carro_id_novo}")
                
                else:
                    # Lógica original para mudança de carro (tipo_solicitacao != 'ativacao')
                    # tipo_carro é um string no formato "UUID|marca|modelo"
                    # Extrair o UUID (carro_id)
                    carro_id = tipo_carro.split('|')[0] if tipo_carro and '|' in tipo_carro else tipo_carro
                    
                    # Verificar se o carro existe na equipe
                    cursor.execute('SELECT id FROM carros WHERE id = %s AND equipe_id = %s', (carro_id, equipe_id))
                    carro_existe = cursor.fetchone()
                    
                    if carro_existe:
                        # É uma mudança de carro existente
                        print(f"[DEBUG] Atualizando status do carro {carro_id} para ativo")
                        # Primeiro, colocar todos os carros da equipe em repouso
                        cursor.execute('UPDATE carros SET status = %s, timestamp_repouso = NOW() WHERE equipe_id = %s', ('repouso', equipe_id))
                        print(f"[DEBUG] Carros da equipe {equipe_id} colocados em repouso")
                        # Depois, ativar o carro solicitado
                        cursor.execute('UPDATE carros SET status = %s, timestamp_ativo = NOW() WHERE id = %s', ('ativo', carro_id))
                        print(f"[DEBUG] Carro {carro_id} atualizado para ativo")
                        print(f"[MUDANÇA CARRO] Carro {carro_id} ativado para equipe {equipe_id}")
                        # Atualizar a equipe para usar o novo carro
                        cursor.execute('UPDATE equipes SET carro_id = %s WHERE id = %s', (carro_id, equipe_id))
                        print(f"[DEBUG] Equipe {equipe_id} atualizada para usar carro {carro_id}")
                        print(f"[EQUIPE ATUALIZADA] Equipe {equipe_id} agora usa carro {carro_id}")
                    else:
                        print(f"[ERRO] Carro {carro_id} não encontrado para equipe {equipe_id}")
                        return False

            # Atualizar status da solicitação
            cursor.execute('''
                UPDATE solicitacoes_carros 
                SET status = %s, data_atualizacao = NOW() 
                WHERE id = %s
            ''', ('aprovado', solicitacao_id))

            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"Erro ao atualizar status da solicitação de carro: {e}")
            import traceback
            traceback.print_exc()
            return False

    def deletar_solicitacao_peca(self, solicitacao_id):
        """Deleta uma solicitação de peça"""
        try:
            conn = self._get_conn()
            cursor = conn.cursor()
            cursor.execute('DELETE FROM solicitacoes_pecas WHERE id = %s', (solicitacao_id,))
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"Erro ao deletar solicitação de peça: {e}")
            return False

    def deletar_solicitacao_carro(self, solicitacao_id):
        """Deleta uma solicitação de carro"""
        try:
            conn = self._get_conn()
            cursor = conn.cursor()
            cursor.execute('DELETE FROM solicitacoes_carros WHERE id = %s', (solicitacao_id,))
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"Erro ao deletar solicitação de carro: {e}")
            return False

    def aprovar_solicitacao_ativacao_carro(self, solicitacao_id: str) -> dict:
        """Aprova uma solicitação de ativação de carro e realiza a troca"""
        try:
            conn = self._get_conn()
            cursor = conn.cursor(dictionary=True)
            
            # Buscar solicitação
            cursor.execute('''
                SELECT id, equipe_id, carro_id, carro_anterior_id, tipo_solicitacao, status
                FROM solicitacoes_carros WHERE id = %s
            ''', (solicitacao_id,))
            
            solicitacao = cursor.fetchone()
            if not solicitacao:
                conn.close()
                return {'sucesso': False, 'erro': 'Solicitação não encontrada'}
            
            if solicitacao['tipo_solicitacao'] != 'ativacao':
                conn.close()
                return {'sucesso': False, 'erro': 'Esta solicitação não é de ativação de carro'}
            
            carro_novo_id = solicitacao['carro_id']
            carro_anterior_id = solicitacao['carro_anterior_id']
            
            print(f"[DB] Aprovando ativação de carro:")
            print(f"[DB]   Carro novo: {carro_novo_id}")
            print(f"[DB]   Carro anterior: {carro_anterior_id}")
            
            # 1. Se havia carro anterior ativo, colocar em repouso
            if carro_anterior_id:
                cursor.execute('''
                    UPDATE carros 
                    SET status = 'repouso', timestamp_repouso = CURRENT_TIMESTAMP
                    WHERE id = %s
                ''', (carro_anterior_id,))
                print(f"[DB]   Carro anterior colocado em repouso: {carro_anterior_id}")
            
            # 2. Ativar o carro novo
            cursor.execute('''
                UPDATE carros 
                SET status = 'ativo', timestamp_ativo = CURRENT_TIMESTAMP
                WHERE id = %s
            ''', (carro_novo_id,))
            print(f"[DB]   Carro novo ativado: {carro_novo_id}")
            
            # 3. Marcar solicitação como aprovada
            cursor.execute('''
                UPDATE solicitacoes_carros 
                SET status = 'aprovada'
                WHERE id = %s
            ''', (solicitacao_id,))
            print(f"[DB]   Solicitação marcada como aprovada: {solicitacao_id}")
            
            conn.commit()
            conn.close()
            
            return {
                'sucesso': True,
                'mensagem': f'Carro ativado com sucesso! Carro anterior colocado em repouso.',
                'carro_novo_id': carro_novo_id,
                'carro_anterior_id': carro_anterior_id
            }
        except Exception as e:
            print(f"[DB] Erro ao aprovar solicitação de ativação: {e}")
            import traceback
            traceback.print_exc()
            return {'sucesso': False, 'erro': str(e)}

    # ============ MÉTODOS DE COMISSÕES ============

    def obter_configuracao(self, chave: str) -> Optional[str]:
        """Obtém o valor de uma configuração"""
        try:
            conn = self._get_conn()
            cursor = conn.cursor()
            cursor.execute('SELECT valor FROM configuracoes WHERE chave = %s', (chave,))
            row = cursor.fetchone()
            conn.close()
            return row[0] if row else None
        except Exception as e:
            print(f"Erro ao obter configuração {chave}: {e}")
            return None

    def salvar_configuracao(self, chave: str, valor: str, descricao: str = '') -> bool:
        """Salva ou atualiza uma configuração"""
        try:
            conn = self._get_conn()
            cursor = conn.cursor()
            
            import uuid
            config_id = str(uuid.uuid4())
            
            cursor.execute('''
                INSERT INTO configuracoes (id, chave, valor, descricao)
                VALUES (%s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                valor = VALUES(valor),
                descricao = VALUES(descricao),
                data_atualizacao = NOW()
            ''', (config_id, chave, valor, descricao))
            
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"Erro ao salvar configuração: {e}")
            return False

    def listar_configuracoes(self) -> List[Dict[str, str]]:
        """Lista todas as configurações"""
        try:
            conn = self._get_conn()
            cursor = conn.cursor()
            cursor.execute('SELECT chave, valor, descricao FROM configuracoes ORDER BY chave')
            rows = cursor.fetchall()
            conn.close()
            
            return [
                {'chave': row[0], 'valor': row[1], 'descricao': row[2] or ''}
                for row in rows
            ]
        except Exception as e:
            print(f"Erro ao listar configurações: {e}")
            return []

    def registrar_comissao(self, tipo: str, valor: float, equipe_id: str = '', equipe_nome: str = '', descricao: str = '') -> bool:
        """Registra uma comissão/pagamento"""
        try:
            conn = self._get_conn()
            cursor = conn.cursor()
            
            import uuid
            comissao_id = str(uuid.uuid4())
            
            cursor.execute('''
                INSERT INTO comissoes (id, tipo, valor_comissao, equipe_id, equipe_nome, descricao)
                VALUES (%s, %s, %s, %s, %s, %s)
            ''', (comissao_id, tipo, valor, equipe_id, equipe_nome, descricao))
            
            conn.commit()
            conn.close()
            print(f"[COMISSÃO] Registrada: tipo={tipo}, valor={valor}, equipe={equipe_nome}")
            return True
        except Exception as e:
            print(f"Erro ao registrar comissão: {e}")
            return False

    def listar_comissoes(self, tipo: str = None, equipe_id: str = None, limit: int = 100) -> List[Dict]:
        """Lista comissões com opção de filtro"""
        try:
            conn = self._get_conn()
            cursor = conn.cursor()
            
            query = 'SELECT id, tipo, valor_comissao, equipe_id, equipe_nome, descricao, data_transacao FROM comissoes WHERE 1=1'
            params = []
            
            if tipo:
                query += ' AND tipo = %s'
                params.append(tipo)
            
            if equipe_id:
                query += ' AND equipe_id = %s'
                params.append(equipe_id)
            
            query += ' ORDER BY data_transacao DESC LIMIT %s'
            params.append(limit)
            
            cursor.execute(query, params)
            rows = cursor.fetchall()
            conn.close()
            
            return [
                {
                    'id': row[0],
                    'tipo': row[1],
                    'valor': row[2],
                    'equipe_id': row[3],
                    'equipe_nome': row[4],
                    'descricao': row[5],
                    'data': row[6].isoformat() if row[6] else ''
                }
                for row in rows
            ]
        except Exception as e:
            print(f"Erro ao listar comissões: {e}")
            return []

    def obter_resumo_comissoes(self, tipo: str = None) -> Dict[str, float]:
        """Obtém resumo de comissões (total por tipo)"""
        try:
            conn = self._get_conn()
            cursor = conn.cursor()
            
            if tipo:
                cursor.execute('''
                    SELECT tipo, SUM(valor_comissao) FROM comissoes 
                    WHERE tipo = %s GROUP BY tipo
                ''', (tipo,))
            else:
                cursor.execute('''
                    SELECT tipo, SUM(valor_comissao) FROM comissoes 
                    GROUP BY tipo
                ''')
            
            rows = cursor.fetchall()
            conn.close()
            
            return {row[0]: float(row[1]) for row in rows}
        except Exception as e:
            print(f"Erro ao obter resumo de comissões: {e}")
            return {}

    # ============ MÉTODOS PIX / MERCADO PAGO ============
    def criar_transacao_pix(self, equipe_id: str, equipe_nome: str, tipo_item: str, 
                           item_id: str, item_nome: str, valor_item: float, valor_taxa: float, 
                           carro_id: str = None, dados_adicionais: dict = None) -> str:
        """Cria uma transação PIX pendente no banco"""
        try:
            import uuid
            import json
            transacao_id = str(uuid.uuid4())
            
            conn = self._get_conn()
            cursor = conn.cursor()
            
            # Verificar se coluna carro_id existe, se não existir cria (para MySQL)
            cursor.execute('''
                SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS 
                WHERE TABLE_NAME='transacoes_pix' AND COLUMN_NAME='carro_id'
            ''')
            
            if not cursor.fetchone():
                try:
                    cursor.execute("ALTER TABLE transacoes_pix ADD COLUMN carro_id VARCHAR(36)")
                    conn.commit()
                    print(f"[PIX] Coluna carro_id adicionada à tabela transacoes_pix")
                except Exception as e:
                    print(f"[PIX] Coluna carro_id pode já existir: {e}")
            
            # Verificar se coluna dados_json existe
            cursor.execute('''
                SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS 
                WHERE TABLE_NAME='transacoes_pix' AND COLUMN_NAME='dados_json'
            ''')
            
            if not cursor.fetchone():
                try:
                    cursor.execute("ALTER TABLE transacoes_pix ADD COLUMN dados_json LONGTEXT")
                    conn.commit()
                    print(f"[PIX] Coluna dados_json adicionada à tabela transacoes_pix")
                except Exception as e:
                    print(f"[PIX] Coluna dados_json pode já existir: {e}")
            
            dados_json_str = json.dumps(dados_adicionais) if dados_adicionais else None
            
            cursor.execute('''
                INSERT INTO transacoes_pix 
                (id, equipe_id, equipe_nome, tipo_item, item_id, item_nome, valor_item, valor_taxa, valor_total, status, carro_id, dados_json)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ''', (
                transacao_id, equipe_id, equipe_nome, tipo_item, item_id, item_nome,
                valor_item, valor_taxa, valor_item + valor_taxa, 'pendente', carro_id, dados_json_str
            ))
            
            conn.commit()
            conn.close()
            
            print(f"[PIX] Transação criada: {transacao_id}, carro_id: {carro_id}")
            return transacao_id
        except Exception as e:
            print(f"Erro ao criar transação PIX: {e}")
            import traceback
            traceback.print_exc()
            return None

    def atualizar_transacao_pix(self, transacao_id: str, mercado_pago_id: str = None, 
                               qr_code: str = '', qr_code_url: str = '') -> bool:
        """Atualiza transação com dados do MercadoPago"""
        try:
            conn = self._get_conn()
            cursor = conn.cursor()
            
            # Construir query dinamicamente para evitar duplicatas de string vazia
            update_fields = []
            params = []
            
            if qr_code is not None:
                update_fields.append('qr_code = %s')
                params.append(qr_code)
            
            if qr_code_url is not None:
                update_fields.append('qr_code_url = %s')
                params.append(qr_code_url)
            
            # Apenas atualizar mercado_pago_id se tiver valor real (não None, não vazio)
            if mercado_pago_id:
                update_fields.append('mercado_pago_id = %s')
                params.append(mercado_pago_id)
            
            params.append(transacao_id)
            
            query = f"UPDATE transacoes_pix SET {', '.join(update_fields)} WHERE id = %s"
            cursor.execute(query, params)
            
            conn.commit()
            conn.close()
            
            return True
        except Exception as e:
            print(f"Erro ao atualizar transação PIX: {e}")
            return False

    def confirmar_transacao_pix(self, mercado_pago_id: str) -> dict:
        """Confirma uma transação PIX após receber webhook do MercadoPago ou confirmação manual"""
        try:
            import uuid
            conn = self._get_conn()
            cursor = conn.cursor(dictionary=True)
            
            # Buscar transação - pode ser por mercado_pago_id ou por id da transação
            cursor.execute('''
                SELECT id, equipe_id, tipo_item, item_id, carro_id FROM transacoes_pix 
                WHERE mercado_pago_id = %s OR id = %s
                LIMIT 1
            ''', (mercado_pago_id, mercado_pago_id))
            row = cursor.fetchone()
            
            if not row:
                conn.close()
                return {'sucesso': False, 'erro': 'Transação não encontrada'}
            
            transacao_id = row['id']
            equipe_id = row['equipe_id']
            tipo_item = row['tipo_item']
            item_id = row['item_id']
            carro_id = row['carro_id']
            
            # Atualizar status da transação
            cursor.execute('''
                UPDATE transacoes_pix 
                SET status = %s, data_confirmacao = CURRENT_TIMESTAMP
                WHERE id = %s
            ''', ('aprovado', transacao_id))
            
            # ===== Se for ativação de carro, criar SOLICITAÇÃO ao invés de ativar direto =====
            if tipo_item == 'carro_ativacao':
                print(f"[DB] Criando solicitação de ativação para carro {item_id}")
                
                # Obter carro anterior que está ativo
                cursor.execute('''
                    SELECT id FROM carros 
                    WHERE equipe_id = %s AND status = 'ativo'
                    LIMIT 1
                ''', (equipe_id,))
                carro_anterior = cursor.fetchone()
                carro_anterior_id = carro_anterior['id'] if carro_anterior else None
                
                # Obter informações do carro a ativar
                cursor.execute('''
                    SELECT marca, modelo FROM carros WHERE id = %s
                ''', (item_id,))
                carro_info = cursor.fetchone()
                tipo_carro = f"{carro_info['marca']} {carro_info['modelo']}" if carro_info else "Desconhecido"
                
                # Criar solicitação de ativação
                solicitacao_id = str(uuid.uuid4())
                cursor.execute('''
                    INSERT INTO solicitacoes_carros 
                    (id, equipe_id, carro_id, carro_anterior_id, tipo_carro, tipo_solicitacao, status)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                ''', (solicitacao_id, equipe_id, item_id, carro_anterior_id, tipo_carro, 'ativacao', 'pendente'))
                
                print(f"[DB] Solicitação criada: {solicitacao_id}")
                print(f"[DB]   Carro a ativar: {item_id}")
                print(f"[DB]   Carro anterior (ativo): {carro_anterior_id}")
            
            # ===== Se for inscrição em etapa com PIX, registrar participação =====
            elif tipo_item == 'inscricao_etapa':
                print(f"[DB] Registrando participação em etapa após PIX confirmado")
                print(f"[DB]   Equipe: {equipe_id}, Etapa: {item_id}, Carro: {carro_id}")
                
                # Extrair dados adicionais (tipo_participacao)
                cursor.execute('''
                    SELECT dados_json FROM transacoes_pix WHERE id = %s
                ''', (transacao_id,))
                tx_row = cursor.fetchone()
                dados_json = tx_row['dados_json'] if tx_row and tx_row['dados_json'] else '{}'
                
                try:
                    import json
                    dados_adicionais = json.loads(dados_json)
                    tipo_participacao = dados_adicionais.get('tipo_participacao', 'piloto')
                except:
                    tipo_participacao = 'piloto'
                
                # Registrar participação na etapa
                participacao_id = str(uuid.uuid4())
                cursor.execute('''
                    INSERT INTO participacoes_etapas 
                    (id, etapa_id, equipe_id, carro_id, tipo_participacao, status, data_inscricao)
                    VALUES (%s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
                    ON DUPLICATE KEY UPDATE 
                    status = 'ativa', 
                    data_inscricao = CURRENT_TIMESTAMP
                ''', (participacao_id, item_id, equipe_id, carro_id, tipo_participacao, 'ativa'))
                
                print(f"[DB] Participação registrada: {participacao_id}")
                print(f"[DB]   Tipo: {tipo_participacao}")
            
            conn.commit()
            cursor.close()
            conn.close()
            
            return {
                'sucesso': True,
                'transacao_id': transacao_id,
                'equipe_id': equipe_id,
                'tipo_item': tipo_item,
                'item_id': item_id,
                'carro_id': carro_id
            }
        except Exception as e:
            print(f"Erro ao confirmar transação PIX: {e}")
            import traceback
            traceback.print_exc()
            return {'erro': str(e)}

    def obter_transacao_pix(self, transacao_id: str) -> dict:
        """Obtém dados de uma transação PIX"""
        try:
            conn = self._get_conn()
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT id, mercado_pago_id, equipe_id, equipe_nome, tipo_item, item_id, item_nome,
                       valor_item, valor_taxa, valor_total, status, qr_code_url, data_criacao, data_confirmacao, carro_id, 
                       COALESCE(dados_json, '{}') as dados_json
                FROM transacoes_pix
                WHERE id = %s
            ''', (transacao_id,))
            
            row = cursor.fetchone()
            conn.close()
            
            if not row:
                return None
            
            return {
                'id': row[0],
                'mercado_pago_id': row[1],
                'equipe_id': row[2],
                'equipe_nome': row[3],
                'tipo_item': row[4],
                'item_id': row[5],
                'item_nome': row[6],
                'valor_item': row[7],
                'valor_taxa': row[8],
                'valor_total': row[9],
                'status': row[10],
                'qr_code_url': row[11],
                'data_criacao': row[12].isoformat() if row[12] else '',
                'data_confirmacao': row[13].isoformat() if row[13] else '',
                'carro_id': row[14],
                'dados_json': row[15]
            }
        except Exception as e:
            print(f"Erro ao obter transação PIX: {e}")
            return None

    def deletar_transacao_pix(self, transacao_id: str) -> bool:
        """Deleta uma transação PIX pendente (quando o usuário cancela)"""
        try:
            conn = self._get_conn()
            cursor = conn.cursor()
            
            print(f"[DB] Deletando transação PIX: {transacao_id}")
            
            cursor.execute('''
                DELETE FROM transacoes_pix
                WHERE id = %s AND status = 'pendente'
            ''', (transacao_id,))
            
            rows_deleted = cursor.rowcount
            conn.commit()
            conn.close()
            
            if rows_deleted > 0:
                print(f"[DB] ✅ Transação {transacao_id} deletada com sucesso")
                return True
            else:
                print(f"[DB] ⚠️ Transação {transacao_id} não foi deletada (pode não estar pendente)")
                return False
        except Exception as e:
            print(f"Erro ao deletar transação PIX: {e}")
            import traceback
            traceback.print_exc()
            return False

    def atualizar_saldo_pix(self, equipe_id: str, valor: float) -> dict:
        """
        Atualiza o saldo PIX de uma equipe
        valor positivo = adiciona ao saldo
        valor negativo = deduz do saldo
        """
        try:
            conn = self._get_conn()
            cursor = conn.cursor()
            
            # Atualizar saldo
            cursor.execute('''
                UPDATE equipes 
                SET saldo_pix = saldo_pix + %s
                WHERE id = %s
            ''', (valor, equipe_id))
            
            # Obter novo saldo
            cursor.execute('SELECT saldo_pix FROM equipes WHERE id = %s', (equipe_id,))
            row = cursor.fetchone()
            novo_saldo = row[0] if row else 0.0
            
            conn.commit()
            conn.close()
            
            print(f"[SALDO PIX] Equipe {equipe_id}: {novo_saldo}")
            return {'sucesso': True, 'novo_saldo': novo_saldo}
        except Exception as e:
            print(f"Erro ao atualizar saldo PIX: {e}")
            import traceback
            traceback.print_exc()
            return {'sucesso': False, 'erro': str(e)}

    def validar_saldo_participacao(self, equipe_id: str, valor_participacao: float) -> dict:
        """
        Valida se a equipe pode participar com o valor
        Permite participação se saldo >= -20.00 reais
        """
        try:
            conn = self._get_conn()
            cursor = conn.cursor()
            
            # Obter saldo atual
            cursor.execute('SELECT saldo_pix FROM equipes WHERE id = %s', (equipe_id,))
            row = cursor.fetchone()
            saldo_atual = row[0] if row else 0.0
            
            conn.close()
            
            # Calcular saldo após participação
            saldo_apos = saldo_atual - valor_participacao
            
            # Validar se pode participar (saldo mínimo de -20)
            pode_participar = saldo_apos >= -20.0
            
            print(f"[VALIDAÇÃO SALDO] Equipe: {equipe_id}")
            print(f"[VALIDAÇÃO SALDO]   Saldo atual: R$ {saldo_atual:.2f}")
            print(f"[VALIDAÇÃO SALDO]   Valor participação: R$ {valor_participacao:.2f}")
            print(f"[VALIDAÇÃO SALDO]   Saldo após: R$ {saldo_apos:.2f}")
            print(f"[VALIDAÇÃO SALDO]   Pode participar: {pode_participar}")
            
            return {
                'pode_participar': pode_participar,
                'saldo_atual': saldo_atual,
                'saldo_apos': saldo_apos,
                'mensagem': 'Participação permitida' if pode_participar else f'Saldo insuficiente. Mínimo permitido: -R$ 20.00'
            }
        except Exception as e:
            print(f"Erro ao validar saldo: {e}")
            import traceback
            traceback.print_exc()
            return {
                'pode_participar': False,
                'erro': str(e)
            }

    def obter_saldo_pix(self, equipe_id: str) -> float:
        """Obtém o saldo PIX atual de uma equipe"""
        try:
            conn = self._get_conn()
            cursor = conn.cursor()
            
            cursor.execute('SELECT saldo_pix FROM equipes WHERE id = %s', (equipe_id,))
            row = cursor.fetchone()
            
            conn.close()
            
            return row[0] if row else 0.0
        except Exception as e:
            print(f"Erro ao obter saldo PIX: {e}")
            return 0.0

    def gerar_pix_participacao(self, equipe_id: str, etapa_id: str, tipo_participacao: str, carro_id: str) -> dict:
        """
        Gera um PIX para participação em uma etapa
        Retorna transacao_id que será usado para gerar o QR code
        """
        try:
            conn = self._get_conn()
            cursor = conn.cursor(dictionary=True)
            
            # 1. Obter dados da equipe
            cursor.execute('SELECT nome, saldo_pix FROM equipes WHERE id = %s', (equipe_id,))
            equipe_result = cursor.fetchone()
            
            if not equipe_result:
                conn.close()
                return {'sucesso': False, 'erro': 'Equipe não encontrada'}
            
            equipe_nome = equipe_result['nome']
            saldo_pix_atual = float(equipe_result.get('saldo_pix', 0))
            
            # 2. Obter valor da participação (configuração global)
            valor_etapa = self.obter_configuracao('valor_etapa')
            valor_etapa_float = float(valor_etapa) if valor_etapa else 1000.00
            
            # 2.1. Verificar se há débito acumulado (saldo <= -valor_etapa)
            if saldo_pix_atual <= -valor_etapa_float:
                # Há débito - cobrar o débito + novo valor
                valor_participacao = abs(saldo_pix_atual) + valor_etapa_float
                print(f"[PIX PARTICIPAÇÃO] Débito detectado: saldo={saldo_pix_atual}, débito={abs(saldo_pix_atual)}, etapa={valor_etapa_float}, total={valor_participacao}")
            else:
                # Sem débito - cobrar apenas o valor da etapa
                valor_participacao = valor_etapa_float
                print(f"[PIX PARTICIPAÇÃO] Sem débito: saldo={saldo_pix_atual}, cobrando apenas valor_etapa={valor_participacao}")
            
            # 3. Obter dados da etapa
            cursor.execute('SELECT nome FROM etapas WHERE id = %s', (etapa_id,))
            etapa_result = cursor.fetchone()
            etapa_nome = etapa_result['nome'] if etapa_result else 'Etapa desconhecida'
            
            conn.close()
            
            # 4. Calcular saldo após cobrança
            saldo_apos_cobranca = saldo_pix_atual - valor_participacao
            print(f"[PIX PARTICIPAÇÃO] Saldo após cobrança: {saldo_apos_cobranca} (mínimo permitido: -20)")
            
            # 4.1. Se saldo ficar < -20, pedir PIX de regularização primeiro
            if saldo_apos_cobranca < -20.0:
                # Calcular quanto precisa pagar para:
                # 1. Quitar o débito (voltar a 0): abs(saldo_atual)
                # 2. Pagar a etapa: valor_etapa
                # Total: abs(saldo_atual) + valor_etapa
                valor_necessario = abs(saldo_pix_atual) + valor_etapa_float
                print(f"[PIX PARTICIPAÇÃO] Insuficiente! Valor necessário para regularizar: R$ {valor_necessario:.2f}")
                
                return {
                    'sucesso': False,
                    'requer_regularizacao': True,
                    'mensagem': f'Você precisa regularizar seu saldo antes de participar desta etapa',
                    'saldo_atual': saldo_pix_atual,
                    'valor_necessario': valor_necessario,
                    'valor_etapa': valor_etapa_float,
                    'etapa_id': etapa_id,
                    'tipo_participacao': tipo_participacao,
                    'carro_id': carro_id
                }
            
            # 4.2. Se saldo >= 0, mostrar opção de "pagar agora" ou "pagar depois"
            if saldo_pix_atual >= 0:
                print(f"[PIX PARTICIPAÇÃO] Saldo positivo ({saldo_pix_atual}). Oferecendo escolha de pagamento")
                
                return {
                    'sucesso': False,
                    'requer_escolha_pagamento': True,
                    'mensagem': f'Escolha como deseja pagar a inscrição',
                    'saldo_atual': saldo_pix_atual,
                    'valor_etapa': valor_etapa_float,
                    'etapa_id': etapa_id,
                    'tipo_participacao': tipo_participacao,
                    'carro_id': carro_id
                }
            
            # 5. Saldo ok (entre 0 e -20) - criar transação PIX de participação
            dados_adicionais = {
                'tipo_participacao': tipo_participacao,
                'carro_id': carro_id,
                'etapa_id': etapa_id
            }
            
            transacao_id = self.criar_transacao_pix(
                equipe_id=equipe_id,
                equipe_nome=equipe_nome,
                tipo_item='participacao_etapa',
                item_id=etapa_id,
                item_nome=f'Participação - {etapa_nome} ({tipo_participacao})',
                valor_item=valor_participacao,
                valor_taxa=0.0,
                carro_id=carro_id,
                dados_adicionais=dados_adicionais
            )
            
            if not transacao_id:
                return {'sucesso': False, 'erro': 'Erro ao criar transação PIX'}
            
            print(f"[PIX PARTICIPAÇÃO] Criada para equipe {equipe_id} - Etapa {etapa_id} - Transação {transacao_id}")
            return {
                'sucesso': True,
                'transacao_id': transacao_id,
                'equipe_id': equipe_id,
                'etapa_id': etapa_id,
                'tipo_participacao': tipo_participacao,
                'valor': valor_participacao,
                'etapa_nome': etapa_nome,
                'saldo_anterior': saldo_pix_atual,
                'saldo_apos': saldo_apos_cobranca
            }
        except Exception as e:
            print(f"Erro ao gerar PIX de participação: {e}")
            import traceback
            traceback.print_exc()
            return {'sucesso': False, 'erro': str(e)}

    def registrar_participacao_com_debito(self, equipe_id: str, etapa_id: str, tipo_participacao: str, carro_id: str) -> dict:
        """
        Registra participação em etapa, deduzindo o valor do saldo_pix como débito
        Usado quando o usuário escolhe "pagar depois" na inscrição
        """
        try:
            import uuid
            conn = self._get_conn()
            cursor = conn.cursor(dictionary=True)
            
            # 1. Obter dados da equipe
            cursor.execute('SELECT nome, saldo_pix FROM equipes WHERE id = %s', (equipe_id,))
            equipe_result = cursor.fetchone()
            
            if not equipe_result:
                conn.close()
                return {'sucesso': False, 'erro': 'Equipe não encontrada'}
            
            saldo_pix_atual = float(equipe_result.get('saldo_pix', 0))
            
            # 2. Obter valor da participação (configuração global)
            valor_etapa = self.obter_configuracao('valor_etapa')
            valor_etapa_float = float(valor_etapa) if valor_etapa else 1000.00
            
            # 3. Verificar se haverá saldo suficiente após deducção
            novo_saldo = saldo_pix_atual - valor_etapa_float
            
            # Não permitir saldo < -20
            if novo_saldo < -20.0:
                conn.close()
                return {
                    'sucesso': False,
                    'erro': f'Saldo insuficiente. Você teria saldo de R$ {novo_saldo:.2f}',
                    'saldo_atual': saldo_pix_atual,
                    'valor_inscricao': valor_etapa_float,
                    'novo_saldo': novo_saldo
                }
            
            # 4. Obter dados da etapa
            cursor.execute('SELECT nome FROM etapas WHERE id = %s', (etapa_id,))
            etapa_result = cursor.fetchone()
            etapa_nome = etapa_result['nome'] if etapa_result else 'Etapa desconhecida'
            
            # 5. Registrar participação
            participacao_id = str(uuid.uuid4())
            cursor.execute('''
                INSERT INTO participacoes_etapas 
                (id, etapa_id, equipe_id, carro_id, tipo_participacao, status, data_inscricao)
                VALUES (%s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
                ON DUPLICATE KEY UPDATE 
                status = 'ativa', 
                data_inscricao = CURRENT_TIMESTAMP
            ''', (participacao_id, etapa_id, equipe_id, carro_id, tipo_participacao, 'ativa'))
            
            # 6. Atualizar saldo_pix com débito
            cursor.execute('''
                UPDATE equipes 
                SET saldo_pix = %s
                WHERE id = %s
            ''', (novo_saldo, equipe_id))
            
            conn.commit()
            conn.close()
            
            print(f"[PARTICIPAÇÃO COM DÉBITO] Registrada para equipe {equipe_id} - Etapa {etapa_id}")
            print(f"[PARTICIPAÇÃO COM DÉBITO] Saldo anterior: R$ {saldo_pix_atual:.2f}")
            print(f"[PARTICIPAÇÃO COM DÉBITO] Saldo novo: R$ {novo_saldo:.2f}")
            
            return {
                'sucesso': True,
                'participacao_id': participacao_id,
                'equipe_id': equipe_id,
                'etapa_id': etapa_id,
                'tipo_participacao': tipo_participacao,
                'valor_deduzido': valor_etapa_float,
                'saldo_anterior': saldo_pix_atual,
                'saldo_novo': novo_saldo,
                'etapa_nome': etapa_nome,
                'mensagem': f'Participação registrada! Você será cobrado R$ {valor_etapa_float:.2f} na próxima etapa'
            }
        except Exception as e:
            print(f"Erro ao registrar participação com débito: {e}")
            import traceback
            traceback.print_exc()
            return {'sucesso': False, 'erro': str(e)}

    def listar_transacoes_pix(self, equipe_id: str = None, status: str = None, limit: int = 100) -> list:
        """Lista transações PIX com filtros opcionais"""
        try:
            conn = self._get_conn()
            cursor = conn.cursor()
            
            query = 'SELECT id, equipe_id, equipe_nome, tipo_item, item_id, item_nome, valor_item, valor_taxa, valor_total, status, qr_code, qr_code_url, data_criacao FROM transacoes_pix WHERE 1=1'
            params = []
            
            if equipe_id:
                query += ' AND equipe_id = %s'
                params.append(equipe_id)
            
            if status:
                query += ' AND status = %s'
                params.append(status)
            
            query += ' ORDER BY data_criacao DESC LIMIT %s'
            params.append(limit)
            
            cursor.execute(query, params)
            rows = cursor.fetchall()
            conn.close()
            
            return [
                {
                    'id': row[0],
                    'equipe_id': row[1],
                    'equipe_nome': row[2],
                    'tipo_item': row[3],
                    'item_id': row[4],
                    'item_nome': row[5],
                    'valor_item': row[6],
                    'valor_taxa': row[7],
                    'valor_total': row[8],
                    'status': row[9],
                    'qr_code': row[10],
                    'qr_code_url': row[11],
                    'data_criacao': row[12].isoformat() if row[12] else ''
                }
                for row in rows
            ]
        except Exception as e:
            print(f"Erro ao listar transações PIX: {e}")
            return []

    def _migrar_remover_coluna_ids_pecas_carros(self) -> None:
        """Migração: remove colunas motor_id, cambio_id, etc. da tabela carros"""
        try:
            conn = self._get_conn()
            cursor = conn.cursor()

            print("[DB] Migrando: removendo colunas de ID de peças da tabela carros...")
            
            # Colunas a remover
            colunas_remover = ['motor_id', 'cambio_id', 'suspensao_id', 'kit_angulo_id', 'diferencial_id']
            
            for coluna in colunas_remover:
                if self._column_exists('carros', coluna):
                    print(f"[DB] Removendo coluna {coluna}...")
                    try:
                        cursor.execute(f'ALTER TABLE carros DROP COLUMN {coluna}')
                        conn.commit()
                    except Exception as e:
                        print(f"[DB] Erro ao remover {coluna}: {e}")
            
            print("[DB] Migração concluída!")
            conn.close()
        except Exception as e:
            print(f"[DB] Erro na migração de remoção de colunas: {e}")

    # ==================== ETAPAS / TEMPORADA ====================
    
    # ==================== CAMPEONATOS ====================
    
    def criar_campeonato(self, campeonato_id: str, nome: str, descricao: str, serie: str, numero_etapas: int) -> bool:
        """Cria um novo campeonato e auto-popula pontuações para todas as equipes da mesma série"""
        try:
            conn = self._get_conn()
            cursor = conn.cursor()
            
            # Criar campeonato
            cursor.execute('''
                INSERT INTO campeonatos (id, nome, descricao, serie, numero_etapas, status)
                VALUES (%s, %s, %s, %s, %s, 'ativo')
                ON DUPLICATE KEY UPDATE
                    nome = VALUES(nome),
                    descricao = VALUES(descricao),
                    numero_etapas = VALUES(numero_etapas),
                    data_atualizacao = CURRENT_TIMESTAMP
            ''', (campeonato_id, nome, descricao, serie, numero_etapas))
            conn.commit()  # Fazer commit primeiro para garantir que o campeonato foi criado
            
            # Obter todas as equipes da mesma série
            cursor.execute('SELECT id FROM equipes WHERE serie = %s', (serie,))
            equipes = cursor.fetchall()
            print(f"[DB] Encontrados {len(equipes)} equipes da série {serie} para adicionar ao campeonato")
            
            # Inserir pontuações para cada equipe
            # Desabilitar foreign key checks para evitar problemas
            cursor.execute("SET FOREIGN_KEY_CHECKS=0")
            
            insercoes_sucesso = 0
            for equipe_row in equipes:
                equipe_id = equipe_row[0]
                pontuacao_id = str(__import__('uuid').uuid4())
                try:
                    cursor.execute('''
                        INSERT INTO pontuacoes_campeonato (id, campeonato_id, equipe_id, pontos, colocacao)
                        VALUES (%s, %s, %s, 0, NULL)
                        ON DUPLICATE KEY UPDATE
                            pontos = 0,
                            colocacao = NULL,
                            data_atualizacao = CURRENT_TIMESTAMP
                    ''', (pontuacao_id, campeonato_id, equipe_id))
                    insercoes_sucesso += 1
                except Exception as duplicate_error:
                    # Ignorar erros de duplicação - a equipe já pode estar registrada
                    print(f"[DB] Nota: Equipe {equipe_id} já existe no campeonato ({duplicate_error})")
            
            # Reabilitar foreign key checks
            cursor.execute("SET FOREIGN_KEY_CHECKS=1")
            
            conn.commit()
            cursor.close()
            conn.close()
            print(f"[DB] [OK] Campeonato criado: {nome} ({serie}) com {insercoes_sucesso}/{len(equipes)} equipes")
            return True
        except Exception as e:
            print(f"[DB] Erro ao criar campeonato: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def listar_campeonatos(self, serie: str = None) -> list:
        """Lista campeonatos com filtros opcionais"""
        try:
            conn = self._get_conn()
            cursor = conn.cursor(dictionary=True)
            
            query = 'SELECT * FROM campeonatos WHERE 1=1'
            params = []
            
            if serie:
                query += ' AND serie = %s'
                params.append(serie)
            
            query += ' ORDER BY data_criacao DESC'
            
            cursor.execute(query, params)
            campeonatos = cursor.fetchall()
            
            cursor.close()
            conn.close()
            return campeonatos or []
        except Exception as e:
            print(f"[DB] Erro ao listar campeonatos: {e}")
            return []
    
    def obter_campeonato(self, campeonato_id: str) -> dict:
        """Obtém um campeonato específico"""
        try:
            conn = self._get_conn()
            cursor = conn.cursor(dictionary=True)
            
            cursor.execute('SELECT * FROM campeonatos WHERE id = %s', (campeonato_id,))
            campeonato = cursor.fetchone()
            
            cursor.close()
            conn.close()
            return campeonato or {}
        except Exception as e:
            print(f"[DB] Erro ao obter campeonato: {e}")
            return {}
    
    def obter_campeonato_anterior_serie(self, serie: str) -> dict:
        """Obtém o campeonato anterior (mais recente) da mesma série para ranking"""
        try:
            conn = self._get_conn()
            cursor = conn.cursor(dictionary=True)
            
            # Buscar o campeonato mais recente da série (que não seja o atual)
            cursor.execute('''
                SELECT * FROM campeonatos 
                WHERE serie = %s 
                ORDER BY data_criacao DESC 
                LIMIT 1
            ''', (serie,))
            
            campeonato = cursor.fetchone()
            cursor.close()
            conn.close()
            return campeonato or None
        except Exception as e:
            print(f"[DB] Erro ao obter campeonato anterior: {e}")
            return None
    
    def obter_equipes_ordenadas_por_pontos(self, campeonato_id: str) -> list:
        """Obtém equipes de um campeonato ordenadas por pontos (crescente)"""
        try:
            conn = self._get_conn()
            cursor = conn.cursor(dictionary=True)
            
            # Buscar pontuações ordenadas por pontos (menor primeiro)
            cursor.execute('''
                SELECT 
                    pc.equipe_id,
                    pc.pontos,
                    e.nome as equipe_nome
                FROM pontuacoes_campeonato pc
                JOIN equipes e ON pc.equipe_id = e.id
                WHERE pc.campeonato_id = %s
                ORDER BY pc.pontos ASC, e.nome ASC
            ''', (campeonato_id,))
            
            equipes = cursor.fetchall()
            cursor.close()
            conn.close()
            return equipes
        except Exception as e:
            print(f"[DB] Erro ao obter equipes ordenadas: {e}")
            return []
    
    def deletar_campeonato(self, campeonato_id: str) -> bool:
        """Deleta um campeonato"""
        try:
            conn = self._get_conn()
            cursor = conn.cursor()
            
            cursor.execute('DELETE FROM campeonatos WHERE id = %s', (campeonato_id,))
            conn.commit()
            cursor.close()
            conn.close()
            return cursor.rowcount > 0
        except Exception as e:
            print(f"[DB] Erro ao deletar campeonato: {e}")
            return False
    
    def obter_pontuacoes_campeonato(self, campeonato_id: str) -> list:
        """Obtém todas as pontuações de um campeonato ordenadas por colocação"""
        try:
            conn = self._get_conn()
            cursor = conn.cursor(dictionary=True)
            
            query = '''
                SELECT 
                    pc.id,
                    pc.campeonato_id,
                    pc.equipe_id,
                    pc.pontos,
                    pc.colocacao,
                    e.nome as equipe_nome
                FROM pontuacoes_campeonato pc
                JOIN equipes e ON pc.equipe_id = e.id
                WHERE pc.campeonato_id = %s
                ORDER BY 
                    CASE WHEN pc.colocacao IS NULL THEN 1 ELSE 0 END,
                    pc.colocacao ASC,
                    pc.pontos DESC
            '''
            
            cursor.execute(query, (campeonato_id,))
            pontuacoes = cursor.fetchall()
            
            cursor.close()
            conn.close()
            return pontuacoes or []
        except Exception as e:
            print(f"[DB] Erro ao obter pontuações do campeonato: {e}")
            return []
    
    def atualizar_pontuacao_equipe(self, campeonato_id: str, equipe_id: str, pontos: int) -> bool:
        """Atualiza os pontos de uma equipe em um campeonato"""
        try:
            conn = self._get_conn()
            cursor = conn.cursor()
            
            cursor.execute('''
                UPDATE pontuacoes_campeonato
                SET pontos = pontos + %s,
                    data_atualizacao = CURRENT_TIMESTAMP
                WHERE campeonato_id = %s AND equipe_id = %s
            ''', (pontos, campeonato_id, equipe_id))
            
            conn.commit()
            cursor.close()
            conn.close()
            return cursor.rowcount > 0
        except Exception as e:
            print(f"[DB] Erro ao atualizar pontuação: {e}")
            return False
    
    def atualizar_colocacoes_campeonato(self, campeonato_id: str) -> bool:
        """Atualiza as colocações de todas as equipes de um campeonato baseado nos pontos"""
        try:
            conn = self._get_conn()
            cursor = conn.cursor()
            
            # Primeiro, resetar as colocações
            cursor.execute('''
                UPDATE pontuacoes_campeonato
                SET colocacao = NULL
                WHERE campeonato_id = %s
            ''', (campeonato_id,))
            
            # Depois, atualizar com novo ranking
            cursor.execute('''
                SELECT 
                    pc.id,
                    ROW_NUMBER() OVER (ORDER BY pc.pontos DESC) as nova_colocacao
                FROM pontuacoes_campeonato pc
                WHERE pc.campeonato_id = %s
            ''', (campeonato_id,))
            
            rankings = cursor.fetchall()
            
            for rank_row in rankings:
                pontuacao_id = rank_row[0]
                colocacao = rank_row[1]
                cursor.execute('''
                    UPDATE pontuacoes_campeonato
                    SET colocacao = %s,
                        data_atualizacao = CURRENT_TIMESTAMP
                    WHERE id = %s
                ''', (colocacao, pontuacao_id))
            
            conn.commit()
            cursor.close()
            conn.close()
            print(f"[DB] ✓ Colocações do campeonato {campeonato_id} atualizadas")
            return True
        except Exception as e:
            print(f"[DB] Erro ao atualizar colocações: {e}")
            return False
    
    def cadastrar_etapa(self, etapa_id: str, campeonato_id: str, numero: int, nome: str, descricao: str, data_etapa: str, hora_etapa: str, serie: str) -> bool:
        """Cadastra uma nova etapa de temporada"""
        try:
            conn = self._get_conn()
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO etapas (id, campeonato_id, numero, nome, descricao, data_etapa, hora_etapa, serie, status)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 'agendada')
                ON DUPLICATE KEY UPDATE
                    campeonato_id = VALUES(campeonato_id),
                    nome = VALUES(nome),
                    descricao = VALUES(descricao),
                    data_etapa = VALUES(data_etapa),
                    hora_etapa = VALUES(hora_etapa),
                    serie = VALUES(serie),
                    data_atualizacao = CURRENT_TIMESTAMP
            ''', (etapa_id, campeonato_id, numero, nome, descricao, data_etapa, hora_etapa, serie))
            
            conn.commit()
            cursor.close()
            conn.close()
            print(f"[DB] ✓ Etapa cadastrada: {nome} ({serie})")
            return True
        except Exception as e:
            print(f"[DB] Erro ao cadastrar etapa: {e}")
            return False
    
    def listar_etapas(self, serie: str = None, status: str = None) -> list:
        """Lista etapas com filtros opcionais"""
        try:
            import datetime
            conn = self._get_conn()
            cursor = conn.cursor(dictionary=True)
            
            query = 'SELECT *, qualificacao_finalizada FROM etapas WHERE 1=1'
            params = []
            
            if serie:
                query += ' AND serie = %s'
                params.append(serie)
            
            if status:
                query += ' AND status = %s'
                params.append(status)
            
            query += ' ORDER BY data_etapa ASC, hora_etapa ASC'
            
            cursor.execute(query, params)
            etapas = cursor.fetchall()
            
            # Converter datetime para string para serialização JSON
            for etapa in etapas:
                # Data
                if etapa.get('data_etapa') is not None:
                    if isinstance(etapa['data_etapa'], datetime.date):
                        etapa['data_etapa'] = etapa['data_etapa'].isoformat()
                    else:
                        etapa['data_etapa'] = str(etapa['data_etapa'])
                
                # Hora (timedelta) - usar 'is not None' porque timedelta(0) é falsy
                if etapa.get('hora_etapa') is not None:
                    if isinstance(etapa['hora_etapa'], datetime.timedelta):
                        total_seconds = int(etapa['hora_etapa'].total_seconds())
                        hours = total_seconds // 3600
                        minutes = (total_seconds % 3600) // 60
                        seconds = total_seconds % 60
                        etapa['hora_etapa'] = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
                    else:
                        etapa['hora_etapa'] = str(etapa['hora_etapa'])
                
                # Data de Início (datetime nullable)
                if etapa.get('data_inicio') is not None:
                    if isinstance(etapa['data_inicio'], datetime.datetime):
                        etapa['data_inicio'] = etapa['data_inicio'].isoformat()
                    else:
                        etapa['data_inicio'] = str(etapa['data_inicio']) if etapa['data_inicio'] else None
                
                # Data de Término (datetime nullable)
                if etapa.get('data_fim') is not None:
                    if isinstance(etapa['data_fim'], datetime.datetime):
                        etapa['data_fim'] = etapa['data_fim'].isoformat()
                    else:
                        etapa['data_fim'] = str(etapa['data_fim']) if etapa['data_fim'] else None
                
                # Timestamps
                if etapa.get('data_criacao') is not None:
                    if isinstance(etapa['data_criacao'], datetime.datetime):
                        etapa['data_criacao'] = etapa['data_criacao'].isoformat()
                    else:
                        etapa['data_criacao'] = str(etapa['data_criacao'])
                
                if etapa.get('data_atualizacao') is not None:
                    if isinstance(etapa['data_atualizacao'], datetime.datetime):
                        etapa['data_atualizacao'] = etapa['data_atualizacao'].isoformat()
                    else:
                        etapa['data_atualizacao'] = str(etapa['data_atualizacao'])
            
            cursor.close()
            conn.close()
            return etapas or []
        except Exception as e:
            print(f"[DB] Erro ao listar etapas: {e}")
            import traceback
            traceback.print_exc()
            return []
    
    def obter_proxima_etapa(self, serie: str) -> dict:
        """Obter a próxima etapa para uma série"""
        try:
            conn = self._get_conn()
            cursor = conn.cursor(dictionary=True)
            
            cursor.execute('''
                SELECT * FROM etapas 
                WHERE serie = %s AND status = 'agendada' AND data_etapa >= CURDATE()
                ORDER BY data_etapa ASC, hora_etapa ASC
                LIMIT 1
            ''', (serie,))
            
            etapa = cursor.fetchone()
            cursor.close()
            conn.close()
            return etapa or {}
        except Exception as e:
            print(f"[DB] Erro ao obter próxima etapa: {e}")
            return {}

    def obter_etapas_piloto(self, piloto_id: str) -> list:
        """Retorna todas as etapas em que o piloto está inscrito"""
        try:
            conn = self._get_conn()
            cursor = conn.cursor(dictionary=True)
            
            cursor.execute('''
                SELECT DISTINCT e.id as etapa_id, e.numero, e.nome, e.data_etapa, e.serie
                FROM etapas e
                JOIN participacoes_etapas pe ON e.id = pe.etapa_id
                WHERE pe.piloto_id = %s
                ORDER BY e.data_etapa ASC
            ''', (piloto_id,))
            
            etapas = cursor.fetchall()
            cursor.close()
            conn.close()
            return etapas or []
        except Exception as e:
            print(f"[DB] Erro ao obter etapas do piloto: {e}")
            return []

    def inscrever_piloto_candidato_etapa(self, etapa_id: str, equipe_id: str, piloto_id: str, piloto_nome: str) -> dict:
        """Inscreve um piloto como candidato para pilotar uma equipe em uma etapa"""
        try:
            import uuid
            
            candidato_id = str(uuid.uuid4())
            
            conn = self._get_conn()
            cursor = conn.cursor(dictionary=True)
            
            # Verificar se equipe existe E obter informações
            cursor.execute('SELECT id, nome FROM equipes WHERE id = %s', (equipe_id,))
            equipe = cursor.fetchone()
            if not equipe:
                cursor.close()
                conn.close()
                return {'sucesso': False, 'erro': 'Equipe não encontrada'}
            
            equipe_nome = equipe['nome']
            
            # Verificar se etapa existe
            cursor.execute('SELECT id FROM etapas WHERE id = %s', (etapa_id,))
            if not cursor.fetchone():
                cursor.close()
                conn.close()
                return {'sucesso': False, 'erro': 'Etapa não encontrada'}
            
            # Verificar se piloto existe
            cursor.execute('SELECT id FROM pilotos WHERE id = %s', (piloto_id,))
            if not cursor.fetchone():
                cursor.close()
                conn.close()
                return {'sucesso': False, 'erro': 'Piloto não encontrado'}
            
            # Obter tipo de participação da equipe nesta etapa
            cursor.execute('''
                SELECT tipo_participacao FROM participacoes_etapas
                WHERE etapa_id = %s AND equipe_id = %s
            ''', (etapa_id, equipe_id))
            
            participacao = cursor.fetchone()
            tipo_participacao = participacao['tipo_participacao'] if participacao else None
            
            # Se tipo é 'tenho_piloto', exigir que piloto esteja vinculado à equipe
            if tipo_participacao == 'tenho_piloto':
                cursor.execute('''
                    SELECT id FROM pilotos_equipes
                    WHERE piloto_id = %s AND equipe_id = %s
                ''', (piloto_id, equipe_id))
                
                if not cursor.fetchone():
                    cursor.close()
                    conn.close()
                    return {
                        'sucesso': False, 
                        'erro': f'Você não está vinculado à equipe "{equipe_nome}". Solicite um código de convite para se vincular.'
                    }
            
            # Se tipo é 'precisa_piloto', permitir qualquer piloto (sem vínculo obrigatório)
            
            # Verificar se piloto já é candidato PARA ESSA MESMA EQUIPE NESSA MESMA ETAPA
            cursor.execute('''
                SELECT id FROM candidatos_piloto_etapa
                WHERE etapa_id = %s AND equipe_id = %s AND piloto_id = %s
            ''', (etapa_id, equipe_id, piloto_id))
            
            if cursor.fetchone():
                cursor.close()
                conn.close()
                return {'sucesso': False, 'erro': 'Piloto já é candidato para esta equipe nesta etapa'}
            
            # IMPORTANTE: Verificar se piloto JÁ se inscreveu para OUTRA EQUIPE na MESMA ETAPA
            cursor.execute('''
                SELECT equipe_id, COUNT(*) as qtd FROM candidatos_piloto_etapa
                WHERE etapa_id = %s AND piloto_id = %s AND status IN ('pendente', 'designado')
                GROUP BY equipe_id
            ''', (etapa_id, piloto_id))
            
            inscricoes_existentes = cursor.fetchall()
            if inscricoes_existentes:
                cursor.close()
                conn.close()
                # Piloto já se inscreveu para outra equipe nesta etapa
                outra_equipe_id = inscricoes_existentes[0]['equipe_id']
                cursor_info = conn.cursor(dictionary=True)
                cursor_info.execute('SELECT nome FROM equipes WHERE id = %s', (outra_equipe_id,))
                outra_equipe = cursor_info.fetchone()
                outra_equipe_nome = outra_equipe['nome'] if outra_equipe else 'desconhecida'
                cursor_info.close()
                
                return {
                    'sucesso': False, 
                    'erro': f'Você já se inscreveu para a equipe "{outra_equipe_nome}" nesta etapa. Um piloto só pode se inscrever para 1 equipe por etapa!'
                }
            
            # Inserir novo candidato
            cursor.execute('''
                INSERT INTO candidatos_piloto_etapa (id, etapa_id, equipe_id, piloto_id, status)
                VALUES (%s, %s, %s, %s, 'pendente')
            ''', (candidato_id, etapa_id, equipe_id, piloto_id))
            
            conn.commit()
            cursor.close()
            conn.close()
            
            print(f"[DB] Piloto {piloto_nome} inscrito como candidato para equipe {equipe_id} na etapa {etapa_id}")
            return {'sucesso': True, 'candidato_id': candidato_id, 'mensagem': f'Você se juntou à equipe! Aguardando designação do admin.'}
        except Exception as e:
            print(f"[DB] Erro ao inscrever piloto como candidato: {e}")
            import traceback
            traceback.print_exc()
            return {'sucesso': False, 'erro': str(e)}

    def inscrever_piloto_etapa(self, etapa_id: str, piloto_id: str, piloto_nome: str) -> dict:
        """Inscreve um piloto em uma etapa (deprecated - usar inscrever_piloto_candidato_etapa)"""
        try:
            import uuid
            
            participacao_id = str(uuid.uuid4())
            
            conn = self._get_conn()
            cursor = conn.cursor()
            
            # Verificar se já está inscrito
            cursor.execute('''
                SELECT id FROM participacoes_etapas
                WHERE etapa_id = %s AND piloto_id = %s
            ''', (etapa_id, piloto_id))
            
            if cursor.fetchone():
                cursor.close()
                conn.close()
                return {'sucesso': False, 'erro': 'Piloto já inscrito nesta etapa'}
            
            # Inserir nova participação (sem equipe_id pois é piloto direto, não de equipe)
            cursor.execute('''
                INSERT INTO participacoes_etapas (id, etapa_id, piloto_id, status)
                VALUES (%s, %s, %s, 'inscrita')
            ''', (participacao_id, etapa_id, piloto_id))
            
            conn.commit()
            cursor.close()
            conn.close()
            
            print(f"[DB] Piloto {piloto_nome} inscrito na etapa {etapa_id}")
            return {'sucesso': True, 'participacao_id': participacao_id}
        except Exception as e:
            print(f"[DB] Erro ao inscrever piloto em etapa: {e}")
            return {'sucesso': False, 'erro': str(e)}
    
    def inscrever_equipe_etapa(self, inscricao_id: str, etapa_id: str, equipe_id: str, carro_id: str, tipo_participacao: str = 'equipe_completa') -> dict:
        """Inscreve uma equipe em uma etapa com tipo de participação e cobra a taxa"""
        try:
            import uuid
            
            if not inscricao_id:
                inscricao_id = str(uuid.uuid4())
            
            conn = self._get_conn()
            cursor = conn.cursor(dictionary=True)
            
            # 1. Obter dados da equipe (saldo_pix)
            cursor.execute('SELECT doricoins, saldo_pix FROM equipes WHERE id = %s', (equipe_id,))
            equipe_result = cursor.fetchone()
            
            if not equipe_result:
                conn.close()
                return {'sucesso': False, 'erro': 'Equipe não encontrada'}
            
            saldo_pix_atual = float(equipe_result.get('saldo_pix', 0))
            
            # 2. Obter valor de participação (configuração global)
            valor_etapa = self.obter_configuracao('valor_etapa')
            valor_etapa_float = float(valor_etapa) if valor_etapa else 1000.00
            
            # 2.1. Verificar se há débito acumulado (saldo <= -valor_etapa)
            if saldo_pix_atual <= -valor_etapa_float:
                # Há débito - cobrar o débito + novo valor
                valor_participacao = abs(saldo_pix_atual) + valor_etapa_float
                print(f"[INSCREVER ETAPA] Débito detectado: saldo={saldo_pix_atual}, total a cobrar={valor_participacao}")
            else:
                # Sem débito - cobrar apenas o valor da etapa
                valor_participacao = valor_etapa_float
                print(f"[INSCREVER ETAPA] Sem débito: cobrando apenas valor_etapa={valor_participacao}")
            
            # 3. Calcular saldo após cobrança
            saldo_apos = saldo_pix_atual - valor_participacao
            print(f"[INSCREVER ETAPA] Saldo após cobrança: {saldo_apos} (mínimo permitido: -20)")
            
            # 3.1. Se saldo ficar < -20, pedir regularização primeiro
            if saldo_apos < -20.0:
                print(f"[INSCREVER ETAPA] ⚠️ Insuficiente! Valor necessário para regularizar: R$ {valor_participacao:.2f}")
                conn.close()
                
                return {
                    'sucesso': False,
                    'requer_regularizacao': True,
                    'mensagem': f'Você precisa regularizar seu saldo antes de participar desta etapa',
                    'saldo_atual': saldo_pix_atual,
                    'valor_necessario': valor_participacao,
                    'valor_etapa': valor_etapa_float,
                    'etapa_id': etapa_id,
                    'tipo_participacao': tipo_participacao,
                    'carro_id': carro_id
                }
            
            # 4. Debitar a taxa de participação do saldo_pix
            novo_saldo_pix = saldo_pix_atual - valor_participacao
            cursor.execute('''
                UPDATE equipes SET saldo_pix = %s WHERE id = %s
            ''', (novo_saldo_pix, equipe_id))
            
            # 5. Registrar a participação
            # Definir piloto_id baseado no tipo de participação
            piloto_id = None
            if tipo_participacao == 'dono_vai_andar':
                # Piloto é a equipe
                piloto_id = equipe_id
            elif tipo_participacao == 'tenho_piloto':
                # Vai ser atribuído depois (quando o piloto for selecionado)
                piloto_id = None
            elif tipo_participacao == 'precisa_piloto':
                # Piloto será atribuído por admin
                piloto_id = None
            
            cursor.execute('''
                INSERT INTO participacoes_etapas (id, etapa_id, equipe_id, carro_id, piloto_id, tipo_participacao, status)
                VALUES (%s, %s, %s, %s, %s, %s, 'inscrita')
                ON DUPLICATE KEY UPDATE tipo_participacao = %s, piloto_id = %s, status = 'inscrita', data_atualizacao = CURRENT_TIMESTAMP
            ''', (inscricao_id, etapa_id, equipe_id, carro_id, piloto_id, tipo_participacao, tipo_participacao, piloto_id))
            
            conn.commit()
            cursor.close()
            conn.close()
            print(f"[DB] ✓ Equipe inscrita na etapa ({tipo_participacao}) - Cobrado: {valor_participacao:.2f} | Saldo novo: {novo_saldo_pix:.2f}")
            return {
                'sucesso': True, 
                'inscricao_id': inscricao_id, 
                'tipo': tipo_participacao,
                'valor_cobrado': valor_participacao,
                'saldo_anterior': saldo_pix_atual,
                'saldo_novo': novo_saldo_pix
            }
        except Exception as e:
            print(f"[DB] Erro ao inscrever equipe: {e}")
            import traceback
            traceback.print_exc()
            return {'sucesso': False, 'erro': str(e)}

    def obter_etapas_equipe(self, equipe_id: str) -> list:
        """Retorna todas as etapas da série da equipe (inscritas ou disponíveis)"""
        try:
            import datetime
            conn = self._get_conn()
            cursor = conn.cursor(dictionary=True)
            
            # Primeiro, obter a série da equipe
            cursor.execute('SELECT id, serie, nome FROM equipes WHERE id = %s', (equipe_id,))
            equipe = cursor.fetchone()
            
            if not equipe:
                cursor.close()
                conn.close()
                return []
            
            serie = equipe.get('serie', '').strip()
            
            # Se serie estiver vazia, tentar obter a partir dos campeonatos da equipe
            if not serie or serie == '':
                cursor.execute('''
                    SELECT DISTINCT c.serie FROM campeonatos c
                    WHERE c.id IN (
                        SELECT DISTINCT e.campeonato_id FROM etapas e
                        WHERE e.id IN (
                            SELECT pe.etapa_id FROM participacoes_etapas pe WHERE pe.equipe_id = %s
                        )
                    )
                ''', (equipe_id,))
                result = cursor.fetchone()
                if result:
                    serie = result.get('serie', '').strip()
            
            if not serie or serie == '':
                # Se ainda não tem série, retornar etapas que a equipe já está inscrita
                cursor.execute('''
                    SELECT e.id, e.numero, e.nome, e.data_etapa, e.hora_etapa, e.serie, e.status,
                           pe.tipo_participacao, pe.piloto_id
                    FROM etapas e
                    INNER JOIN participacoes_etapas pe ON e.id = pe.etapa_id
                    WHERE pe.equipe_id = %s
                    ORDER BY e.data_etapa ASC
                ''', (equipe_id,))
            else:
                # Retornar TODAS as etapas para essa série, com LEFT JOIN para verificar se inscrita
                cursor.execute('''
                    SELECT e.id, e.numero, e.nome, e.data_etapa, e.hora_etapa, e.serie, e.status,
                           pe.tipo_participacao, pe.piloto_id
                    FROM etapas e
                    LEFT JOIN participacoes_etapas pe ON e.id = pe.etapa_id AND pe.equipe_id = %s
                    WHERE e.serie = %s
                    ORDER BY e.data_etapa ASC
                ''', (equipe_id, serie))
            
            etapas_raw = cursor.fetchall()
            etapas = []
            
            for etapa_raw in etapas_raw:
                try:
                    etapa = dict(etapa_raw)
                    
                    # Converter data_etapa
                    if 'data_etapa' in etapa and etapa['data_etapa']:
                        if isinstance(etapa['data_etapa'], datetime.date):
                            etapa['data_etapa'] = etapa['data_etapa'].isoformat()
                        elif etapa['data_etapa']:
                            etapa['data_etapa'] = str(etapa['data_etapa'])
                    
                    # Converter hora_etapa (timedelta ou TIME)
                    if 'hora_etapa' in etapa and etapa['hora_etapa']:
                        if isinstance(etapa['hora_etapa'], datetime.timedelta):
                            total_seconds = int(etapa['hora_etapa'].total_seconds())
                            hours = total_seconds // 3600
                            minutes = (total_seconds % 3600) // 60
                            seconds = total_seconds % 60
                            etapa['hora_etapa'] = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
                        else:
                            etapa['hora_etapa'] = str(etapa['hora_etapa'])
                    
                    etapas.append(etapa)
                except Exception as e:
                    pass
            
            # GARANTIA FINAL: Converter QUALQUER timedelta ou datetime que possa ter sobrado
            final_etapas = []
            for etapa in etapas:
                final_etapa = {}
                for key, value in etapa.items():
                    if value is None:
                        final_etapa[key] = None
                    elif isinstance(value, datetime.timedelta):
                        total_seconds = int(value.total_seconds())
                        hours = total_seconds // 3600
                        minutes = (total_seconds % 3600) // 60
                        seconds = total_seconds % 60
                        final_etapa[key] = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
                    elif isinstance(value, (datetime.datetime, datetime.date)):
                        final_etapa[key] = value.isoformat()
                    else:
                        final_etapa[key] = value
                final_etapas.append(final_etapa)
            
            cursor.close()
            conn.close()
            return final_etapas
        except Exception as e:
            print(f"[DB] Erro ao obter etapas da equipe: {e}")
            import traceback
            traceback.print_exc()
            return []

    def listar_pilotos(self) -> list:
        """Retorna lista de todos os pilotos"""
        try:
            conn = self._get_conn()
            cursor = conn.cursor(dictionary=True)
            
            cursor.execute('SELECT id, nome FROM pilotos ORDER BY nome ASC')
            pilotos = cursor.fetchall()
            cursor.close()
            conn.close()
            return pilotos or []
        except Exception as e:
            print(f"[DB] Erro ao listar pilotos: {e}")
            return []

    def obter_equipes_precisando_piloto(self, etapa_id: str) -> list:
        """Retorna equipes que precisam de piloto em uma etapa"""
        try:
            conn = self._get_conn()
            cursor = conn.cursor(dictionary=True)
            
            cursor.execute('''
                SELECT pe.id, e.id as equipe_id, e.nome as equipe_nome, pe.tipo_participacao
                FROM participacoes_etapas pe
                JOIN equipes e ON pe.equipe_id = e.id
                WHERE pe.etapa_id = %s AND pe.tipo_participacao = 'precisa_piloto'
                ORDER BY e.nome
            ''', (etapa_id,))
            
            equipes = cursor.fetchall()
            cursor.close()
            conn.close()
            return equipes or []
        except Exception as e:
            print(f"[DB] Erro ao obter equipes precisando piloto: {e}")
            return []

    def obter_pontos_por_colocacao(self, colocacao: int) -> int:
        """Retorna os pontos baseado na colocacao"""
        if colocacao == 1:
            return 100
        elif colocacao == 2:
            return 88
        elif colocacao == 3:
            return 76
        elif colocacao == 4:
            return 64
        elif 5 <= colocacao <= 8:
            return 48
        elif 9 <= colocacao <= 16:
            return 32
        elif 17 <= colocacao <= 32:
            return 16
        else:
            return 0

    def calcular_colocacoes_etapa(self, etapa_id: str, campeonato_id: str) -> dict:
        """Calcula as colocacoes baseado em vitorias"""
        try:
            conn = self._get_conn()
            cursor = conn.cursor(dictionary=True)
            
            cursor.execute('''
                SELECT b.etapa, b.equipe_a_id, b.equipe_b_id, b.resultado
                FROM batalhas b
                WHERE b.etapa = (SELECT numero FROM etapas WHERE id = %s)
            ''', (etapa_id,))
            
            batalhas = cursor.fetchall()
            vitorias = {}
            
            for batalha in batalhas:
                equipe_a = batalha['equipe_a_id']
                equipe_b = batalha['equipe_b_id']
                resultado = batalha['resultado']
                
                if equipe_a not in vitorias:
                    vitorias[equipe_a] = 0
                if equipe_b not in vitorias:
                    vitorias[equipe_b] = 0
                
                if resultado == "equipe_a_venceu":
                    vitorias[equipe_a] += 1
                elif resultado == "equipe_b_venceu":
                    vitorias[equipe_b] += 1
            
            equipes_ordenadas = sorted(vitorias.items(), key=lambda x: x[1], reverse=True)
            colocacoes = []
            colocacao_atual = 1
            vitoria_anterior = None
            
            for i, (equipe_id, num_vitorias) in enumerate(equipes_ordenadas):
                if vitoria_anterior is not None and num_vitorias < vitoria_anterior:
                    colocacao_atual = i + 1
                colocacoes.append((equipe_id, colocacao_atual, num_vitorias))
                vitoria_anterior = num_vitorias
            
            cursor.close()
            conn.close()
            return {'sucesso': True, 'colocacoes': colocacoes}
        except Exception as e:
            return {'sucesso': False, 'colocacoes': [], 'erro': str(e)}

    def atribuir_pontos_etapa(self, etapa_id: str, campeonato_id: str) -> dict:
        """Calcula e atribui pontos para cada equipe na etapa"""
        try:
            conn = self._get_conn()
            cursor = conn.cursor(dictionary=True)
            
            resultado_colocacoes = self.calcular_colocacoes_etapa(etapa_id, campeonato_id)
            if not resultado_colocacoes['sucesso']:
                return resultado_colocacoes
            
            colocacoes = resultado_colocacoes['colocacoes']
            pontuacoes_criadas = []
            
            for equipe_id, colocacao, vitorias in colocacoes:
                pontos = self.obter_pontos_por_colocacao(colocacao)
                pontuacoes_criadas.append({'equipe_id': equipe_id, 'colocacao': colocacao, 'pontos': pontos})
                
                # Atualizar pontos na tabela pontuacoes_campeonato
                try:
                    self.atualizar_pontuacao_equipe(campeonato_id, equipe_id, pontos)
                except Exception as update_error:
                    print(f"[DB] Aviso ao atualizar pontuação de {equipe_id}: {update_error}")
            
            # Atualizar colocações
            try:
                self.atualizar_colocacoes_campeonato(campeonato_id)
            except Exception as rank_error:
                print(f"[DB] Aviso ao atualizar colocações: {rank_error}")
            
            cursor.close()
            conn.close()
            return {'sucesso': True, 'pontuacoes': pontuacoes_criadas}
        except Exception as e:
            return {'sucesso': False, 'erro': str(e)}

    def alocar_piloto_equipe_etapa(self, participacao_id: str, piloto_id: str) -> dict:
        """Aloca um piloto a uma equipe em uma etapa"""
        try:
            conn = self._get_conn()
            cursor = conn.cursor()
            
            cursor.execute('''
                UPDATE participacoes_etapas 
                SET piloto_id = %s, tipo_participacao = 'equipe_completa'
                WHERE id = %s
            ''', (piloto_id, participacao_id))
            
            conn.commit()
            cursor.close()
            conn.close()
            print(f"[DB] ✓ Piloto alocado à participação")
            return {'sucesso': True}
        except Exception as e:
            print(f"[DB] Erro ao alocar piloto: {e}")
            return {'sucesso': False, 'erro': str(e)}
    
    def aplicar_ordenacao_qualificacao(self, etapa_id: str) -> dict:
        """Aplica ordenação de qualificação baseada no campeonato anterior (por pontos)"""
        try:
            conn = self._get_conn()
            cursor = conn.cursor(dictionary=True)
            
            # 1. Buscar a etapa e seu campeonato
            cursor.execute('''
                SELECT e.id, e.campeonato_id, c.serie
                FROM etapas e
                JOIN campeonatos c ON e.campeonato_id = c.id
                WHERE e.id = %s
            ''', (etapa_id,))
            
            etapa_info = cursor.fetchone()
            if not etapa_info:
                return {'sucesso': False, 'erro': 'Etapa não encontrada'}
            
            campeonato_atual_id = etapa_info['campeonato_id']
            serie = etapa_info['serie']
            
            # 2. Buscar todas as participações da etapa
            cursor.execute('''
                SELECT id, equipe_id
                FROM participacoes_etapas
                WHERE etapa_id = %s
                ORDER BY id
            ''', (etapa_id,))
            
            participacoes = cursor.fetchall()
            equipes_ids = [p['equipe_id'] for p in participacoes]
            
            ordem_equipes = []
            
            # 3. Tentar buscar o campeonato anterior da mesma série
            cursor.execute('''
                SELECT id FROM campeonatos 
                WHERE serie = %s AND id != %s
                ORDER BY data_criacao DESC 
                LIMIT 1
            ''', (serie, campeonato_atual_id))
            
            campeonato_anterior = cursor.fetchone()
            
            if campeonato_anterior:
                # Existe campeonato anterior - ordenar por pontos
                campeonato_anterior_id = campeonato_anterior['id']
                
                # Buscar pontos de cada equipe no campeonato anterior
                cursor.execute('''
                    SELECT equipe_id, pontos
                    FROM pontuacoes_campeonato
                    WHERE campeonato_id = %s
                    ORDER BY pontos ASC, equipe_id ASC
                ''', (campeonato_anterior_id,))
                
                pontuacoes = cursor.fetchall()
                pontuacoes_dict = {p['equipe_id']: p['pontos'] for p in pontuacoes}
                
                # Ordenar equipes pelos pontos (menor primeiro)
                ordem_equipes = sorted(equipes_ids, key=lambda eid: pontuacoes_dict.get(eid, float('inf')))
                
                print(f"[DB] ✓ Qualificação ordenada pelos pontos do campeonato anterior")
            else:
                # Não existe campeonato anterior - ordenar aleatoriamente
                import random
                ordem_equipes = equipes_ids.copy()
                random.shuffle(ordem_equipes)
                print(f"[DB] ✓ Qualificação ordenada aleatoriamente (nenhum campeonato anterior)")
            
            # 4. Atualizar a ordem de qualificação nas participações
            for idx, equipe_id in enumerate(ordem_equipes, 1):
                # Encontrar a participação dessa equipe
                participacao_id = next(
                    (p['id'] for p in participacoes if p['equipe_id'] == equipe_id),
                    None
                )
                
                if participacao_id:
                    cursor.execute('''
                        UPDATE participacoes_etapas
                        SET ordem_qualificacao = %s
                        WHERE id = %s
                    ''', (idx, participacao_id))
            
            conn.commit()
            cursor.close()
            conn.close()
            
            return {
                'sucesso': True,
                'mensagem': f'Qualificação ordenada para {len(ordem_equipes)} equipes',
                'tem_campeonato_anterior': campeonato_anterior is not None,
                'ordem_equipes': ordem_equipes
            }
            
        except Exception as e:
            print(f"[DB] Erro ao aplicar ordenação de qualificação: {e}")
            import traceback
            traceback.print_exc()
            return {'sucesso': False, 'erro': str(e)}

    def atualizar_etapa_datas(self, etapa_id: str, data_inicio: str = None, data_fim: str = None) -> dict:
        """Atualiza as datas de início e fim de uma etapa"""
        try:
            conn = self._get_conn()
            cursor = conn.cursor()
            
            # Converter string ISO para datetime MySQL
            from datetime import datetime
            dt_inicio = None
            dt_fim = None
            
            if data_inicio:
                dt_inicio = datetime.fromisoformat(data_inicio.replace('T', ' ').split('.')[0])
            if data_fim:
                dt_fim = datetime.fromisoformat(data_fim.replace('T', ' ').split('.')[0])
            
            cursor.execute('''
                UPDATE etapas 
                SET data_inicio = %s, data_fim = %s
                WHERE id = %s
            ''', (dt_inicio, dt_fim, etapa_id))
            
            conn.commit()
            cursor.close()
            conn.close()
            print(f"[DB] ✓ Datas da etapa atualizadas")
            return {'sucesso': True, 'mensagem': 'Etapa atualizada com sucesso'}
        except Exception as e:
            print(f"[DB] Erro ao atualizar etapa: {e}")
            return {'sucesso': False, 'erro': str(e)}
    

    def validar_pecas_carro(self, carro_id: str, equipe_id: str) -> dict:
        """Valida se o carro tem todas as peças necessárias instaladas"""
        try:
            conn = self._get_conn()
            cursor = conn.cursor(dictionary=True)
            
            tipos_necessarios = ['motor', 'cambio', 'suspensao', 'kit_angulo', 'diferencial']
            pecas_faltando = []
            
            for tipo in tipos_necessarios:
                cursor.execute('''
                    SELECT COUNT(*) as qtd FROM pecas 
                    WHERE carro_id = %s AND tipo = %s AND instalado = 1
                ''', (carro_id, tipo))
                
                resultado = cursor.fetchone()
                if resultado['qtd'] == 0:
                    pecas_faltando.append(tipo)
            
            cursor.close()
            conn.close()
            
            return {
                'valido': len(pecas_faltando) == 0,
                'pecas_faltando': pecas_faltando,
                'faltam': len(pecas_faltando)
            }
        except Exception as e:
            print(f"[DB] Erro ao validar peças: {e}")
            return {'valido': False, 'pecas_faltando': tipos_necessarios, 'faltam': 5}

    def verificar_peca_carro(self, carro_id: str, equipe_id: str, tipo_peca: str) -> bool:
        """Verifica se o carro tem uma peça específica instalada"""
        try:
            conn = self._get_conn()
            cursor = conn.cursor(dictionary=True)
            
            # Procurar peça instalada (instalado = 1) do tipo especificado
            cursor.execute('''
                SELECT COUNT(*) as qtd FROM pecas 
                WHERE carro_id = %s AND tipo = %s AND instalado = 1
            ''', (carro_id, tipo_peca))
            
            resultado = cursor.fetchone()
            cursor.close()
            conn.close()
            
            return resultado['qtd'] > 0 if resultado else False
        except Exception as e:
            print(f"[DB] Erro ao verificar peça: {e}")
            return False

    # ========== MÉTODOS DE PILOTOS E EQUIPES ==========
    
    def gerar_codigo_convite(self, equipe_id: str) -> dict:
        """Gera um código de convite para pilotos se vincularem à equipe"""
        try:
            import uuid
            import string
            import random
            
            conn = self._get_conn()
            cursor = conn.cursor(dictionary=True)
            
            # Gerar código único
            codigo = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
            convite_id = str(uuid.uuid4())
            
            # Verificar se a equipe existe
            cursor.execute('SELECT id FROM equipes WHERE id = %s', (equipe_id,))
            if not cursor.fetchone():
                conn.close()
                return {'sucesso': False, 'erro': 'Equipe não encontrada'}
            
            # Inserir novo código de convite
            cursor.execute('''
                INSERT INTO convites_pilotos (id, equipe_id, codigo, usos_restantes)
                VALUES (%s, %s, %s, %s)
            ''', (convite_id, equipe_id, codigo, 10))
            
            conn.commit()
            cursor.close()
            conn.close()
            
            print(f"[DB] ✓ Código de convite gerado: {codigo}")
            return {
                'sucesso': True,
                'codigo': codigo,
                'mensagem': f'Código gerado com sucesso: {codigo}'
            }
        except Exception as e:
            print(f"[DB] Erro ao gerar código de convite: {e}")
            return {'sucesso': False, 'erro': str(e)}
    
    def vincular_piloto_a_equipe(self, piloto_id: str, codigo_convite: str) -> dict:
        """Vincula um piloto a uma equipe usando código de convite"""
        try:
            import uuid
            
            conn = self._get_conn()
            cursor = conn.cursor(dictionary=True)
            
            # Verificar se o código é válido
            cursor.execute('''
                SELECT id, equipe_id, usos_restantes FROM convites_pilotos 
                WHERE codigo = %s AND status = 'ativo'
            ''', (codigo_convite.upper(),))
            
            convite = cursor.fetchone()
            if not convite:
                conn.close()
                return {'sucesso': False, 'erro': 'Código de convite inválido ou expirado'}
            
            if convite['usos_restantes'] <= 0:
                conn.close()
                return {'sucesso': False, 'erro': 'Este código de convite não possui mais usos'}
            
            equipe_id = convite['equipe_id']
            
            # Verificar se o piloto já está vinculado a esta equipe
            cursor.execute('''
                SELECT id FROM pilotos_equipes 
                WHERE piloto_id = %s AND equipe_id = %s
            ''', (piloto_id, equipe_id))
            
            if cursor.fetchone():
                conn.close()
                return {'sucesso': False, 'erro': 'Piloto já vinculado a esta equipe'}
            
            # Criar vínculo
            vínculo_id = str(uuid.uuid4())
            cursor.execute('''
                INSERT INTO pilotos_equipes (id, piloto_id, equipe_id, codigo_convite)
                VALUES (%s, %s, %s, %s)
            ''', (vínculo_id, piloto_id, equipe_id, codigo_convite.upper()))
            
            # Decrementar usos restantes
            cursor.execute('''
                UPDATE convites_pilotos SET usos_restantes = usos_restantes - 1
                WHERE codigo = %s
            ''', (codigo_convite.upper(),))
            
            conn.commit()
            
            # Obter informações da equipe
            cursor.execute('SELECT nome FROM equipes WHERE id = %s', (equipe_id,))
            equipe = cursor.fetchone()
            
            cursor.close()
            conn.close()
            
            print(f"[DB] ✓ Piloto {piloto_id} vinculado à equipe {equipe_id}")
            return {
                'sucesso': True,
                'mensagem': f'Vinculado à equipe {equipe["nome"]}',
                'equipe_id': equipe_id,
                'equipe_nome': equipe['nome']
            }
        except Exception as e:
            print(f"[DB] Erro ao vincular piloto à equipe: {e}")
            return {'sucesso': False, 'erro': str(e)}
    
    def listar_equipes_do_piloto(self, piloto_id: str) -> dict:
        """Lista todas as equipes vinculadas a um piloto"""
        try:
            conn = self._get_conn()
            cursor = conn.cursor(dictionary=True)
            
            cursor.execute('''
                SELECT e.id, e.nome
                FROM pilotos_equipes pe
                JOIN equipes e ON pe.equipe_id = e.id
                WHERE pe.piloto_id = %s AND pe.status = 'ativo'
                ORDER BY e.nome
            ''', (piloto_id,))
            
            equipes = cursor.fetchall()
            cursor.close()
            conn.close()
            
            print(f"[DB] ✓ {len(equipes)} equipes encontradas para piloto {piloto_id}")
            return {
                'sucesso': True,
                'equipes': equipes,
                'total': len(equipes)
            }
        except Exception as e:
            print(f"[DB] Erro ao listar equipes do piloto: {e}")
            return {'sucesso': False, 'erro': str(e), 'equipes': []}
    
    def listar_pilotos_da_equipe(self, equipe_id: str) -> dict:
        """Lista todos os pilotos vinculados a uma equipe"""
        try:
            conn = self._get_conn()
            cursor = conn.cursor(dictionary=True)
            
            cursor.execute('''
                SELECT p.id, p.nome
                FROM pilotos_equipes pe
                JOIN pilotos p ON pe.piloto_id = p.id
                WHERE pe.equipe_id = %s AND pe.status = 'ativo'
                ORDER BY p.nome
            ''', (equipe_id,))
            
            pilotos = cursor.fetchall()
            cursor.close()
            conn.close()
            
            print(f"[DB] ✓ {len(pilotos)} pilotos encontrados para equipe {equipe_id}")
            return {
                'sucesso': True,
                'pilotos': pilotos,
                'total': len(pilotos)
            }
        except Exception as e:
            print(f"[DB] Erro ao listar pilotos da equipe: {e}")
            return {'sucesso': False, 'erro': str(e), 'pilotos': []}
    
    def desincular_piloto_de_equipe(self, piloto_id: str, equipe_id: str) -> dict:
        """Remove o vínculo entre um piloto e uma equipe"""
        try:
            conn = self._get_conn()
            cursor = conn.cursor()
            
            cursor.execute('''
                UPDATE pilotos_equipes 
                SET status = 'inativo'
                WHERE piloto_id = %s AND equipe_id = %s
            ''', (piloto_id, equipe_id))
            
            if cursor.rowcount == 0:
                conn.close()
                return {'sucesso': False, 'erro': 'Vínculo não encontrado'}
            
            conn.commit()
            cursor.close()
            conn.close()
            
            print(f"[DB] ✓ Piloto {piloto_id} desvinculado da equipe {equipe_id}")
            return {'sucesso': True, 'mensagem': 'Desvinculado com sucesso'}
        except Exception as e:
            print(f"[DB] Erro ao desincular piloto: {e}")
            return {'sucesso': False, 'erro': str(e)}
    
    def obter_equipes_etapa(self, etapa_id: str) -> list:
        """Retorna equipes inscritas em uma etapa com tipo de participação"""
        try:
            conn = self._get_conn()
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT 
                    pe.equipe_id,
                    e.nome as equipe_nome,
                    pe.tipo_participacao,
                    pe.carro_id
                FROM participacoes_etapas pe
                INNER JOIN equipes e ON pe.equipe_id = e.id
                WHERE pe.etapa_id = %s 
                AND pe.status IN ('ativa', 'inscrita')
                AND pe.tipo_participacao IN ('tenho_piloto', 'precisa_piloto')
            ''', (etapa_id,))
            
            equipes = []
            for row in cursor.fetchall():
                equipes.append({
                    'equipe_id': row[0],
                    'equipe_nome': row[1],
                    'tipo_participacao': row[2],
                    'carro_id': row[3]
                })
            
            cursor.close()
            conn.close()
            
            print(f"[DB] ✓ {len(equipes)} equipes encontradas para etapa {etapa_id}")
            return equipes
        except Exception as e:
            print(f"[DB] Erro ao buscar equipes da etapa: {e}")
            return []

    def obter_candidatos_piloto_etapa(self, etapa_id: str) -> list:
        """Retorna lista de candidatos pilotos agrupados por equipe para uma etapa"""
        try:
            conn = self._get_conn()
            cursor = conn.cursor(dictionary=True)
            
            # Buscar todos os candidatos pendentes para essa etapa
            # Apenas de equipes que têm tipo_participacao = 'precisa_piloto' E ainda não têm piloto_id designado
            cursor.execute('''
                SELECT 
                    cpe.id as candidato_id,
                    cpe.etapa_id,
                    cpe.equipe_id,
                    e.nome as equipe_nome,
                    cpe.piloto_id,
                    p.nome as piloto_nome,
                    cpe.status,
                    cpe.data_inscricao,
                    pe.tipo_participacao
                FROM candidatos_piloto_etapa cpe
                INNER JOIN equipes e ON cpe.equipe_id = e.id
                INNER JOIN pilotos p ON cpe.piloto_id = p.id
                INNER JOIN participacoes_etapas pe ON cpe.etapa_id = pe.etapa_id AND cpe.equipe_id = pe.equipe_id
                WHERE cpe.etapa_id = %s 
                  AND cpe.status = 'pendente'
                  AND pe.tipo_participacao = 'precisa_piloto'
                  AND pe.piloto_id IS NULL
                ORDER BY e.nome, cpe.data_inscricao
            ''', (etapa_id,))
            
            candidatos_raw = cursor.fetchall()
            
            # Agrupar por equipe
            candidatos_por_equipe = {}
            for row in candidatos_raw:
                equipe_id = row['equipe_id']
                if equipe_id not in candidatos_por_equipe:
                    candidatos_por_equipe[equipe_id] = {
                        'equipe_id': equipe_id,
                        'equipe_nome': row['equipe_nome'],
                        'tipo_participacao': row['tipo_participacao'],
                        'candidatos': []
                    }
                
                candidatos_por_equipe[equipe_id]['candidatos'].append({
                    'candidato_id': row['candidato_id'],
                    'piloto_id': row['piloto_id'],
                    'piloto_nome': row['piloto_nome'],
                    'status': row['status'],
                    'data_inscricao': row['data_inscricao'].isoformat() if row['data_inscricao'] else None
                })
            
            cursor.close()
            conn.close()
            
            resultado = list(candidatos_por_equipe.values())
            print(f"[DB] ✓ {len(candidatos_por_equipe)} equipes com candidatos encontradas")
            return resultado
        except Exception as e:
            print(f"[DB] Erro ao buscar candidatos pilotos: {e}")
            import traceback
            traceback.print_exc()
            return []

    def obter_candidatura_piloto_etapa(self, piloto_id: str, etapa_id: str) -> dict:
        """Retorna a candidatura ativa do piloto para uma etapa (se houver)"""
        try:
            conn = self._get_conn()
            cursor = conn.cursor(dictionary=True)
            
            # Buscar candidatura ativa (pendente ou designado) para esta etapa
            cursor.execute('''
                SELECT 
                    cpe.id,
                    cpe.equipe_id,
                    e.nome as equipe_nome,
                    cpe.status
                FROM candidatos_piloto_etapa cpe
                INNER JOIN equipes e ON cpe.equipe_id = e.id
                WHERE cpe.piloto_id = %s AND cpe.etapa_id = %s 
                  AND cpe.status IN ('pendente', 'designado')
                LIMIT 1
            ''', (piloto_id, etapa_id))
            
            resultado = cursor.fetchone()
            cursor.close()
            conn.close()
            
            if resultado:
                return {
                    'candidato_id': resultado['id'],
                    'equipe_id': resultado['equipe_id'],
                    'equipe_nome': resultado['equipe_nome'],
                    'status': resultado['status']
                }
            return None
        except Exception as e:
            print(f"[DB] Erro ao buscar candidatura do piloto: {e}")
            import traceback
            traceback.print_exc()
            return None

    def designar_piloto_etapa(self, candidato_id: str) -> dict:
        """Designa um piloto candidato para pilotar uma equipe em uma etapa"""
        try:
            conn = self._get_conn()
            cursor = conn.cursor(dictionary=True)
            
            # 1. Obter dados do candidato
            cursor.execute('''
                SELECT etapa_id, equipe_id, piloto_id FROM candidatos_piloto_etapa
                WHERE id = %s
            ''', (candidato_id,))
            
            candidato = cursor.fetchone()
            if not candidato:
                cursor.close()
                conn.close()
                return {'sucesso': False, 'erro': 'Candidato não encontrado'}
            
            etapa_id = candidato['etapa_id']
            equipe_id = candidato['equipe_id']
            piloto_id = candidato['piloto_id']
            
            # 2. Atualizar status do candidato para "designado"
            cursor.execute('''
                UPDATE candidatos_piloto_etapa
                SET status = 'designado'
                WHERE id = %s
            ''', (candidato_id,))
            
            # 3. Atualizar a participação da equipe na etapa para adicionar piloto_id
            cursor.execute('''
                UPDATE participacoes_etapas
                SET piloto_id = %s
                WHERE etapa_id = %s AND equipe_id = %s
            ''', (piloto_id, etapa_id, equipe_id))
            
            # 4. Se não houver participação ainda, criar uma com piloto designado
            if cursor.rowcount == 0:
                import uuid
                participacao_id = str(uuid.uuid4())
                cursor.execute('''
                    SELECT carro_id, tipo_participacao FROM participacoes_etapas
                    WHERE etapa_id = %s AND equipe_id = %s
                    LIMIT 1
                ''', (etapa_id, equipe_id))
                
                part = cursor.fetchone()
                carro_id = part['carro_id'] if part else None
                tipo_participacao = part['tipo_participacao'] if part else 'tenho_piloto'
                
                cursor.execute('''
                    INSERT INTO participacoes_etapas 
                    (id, etapa_id, equipe_id, piloto_id, carro_id, tipo_participacao, status)
                    VALUES (%s, %s, %s, %s, %s, %s, 'ativa')
                ''', (participacao_id, etapa_id, equipe_id, piloto_id, carro_id, tipo_participacao))
            
            conn.commit()
            cursor.close()
            conn.close()
            
            print(f"[DB] ✓ Piloto {piloto_id} designado para equipe {equipe_id} na etapa {etapa_id}")
            return {'sucesso': True, 'mensagem': 'Piloto designado com sucesso'}
        except Exception as e:
            print(f"[DB] Erro ao designar piloto: {e}")
            import traceback
            traceback.print_exc()
            return {'sucesso': False, 'erro': str(e)}
    
    def cancelar_candidatura_piloto_etapa(self, candidato_id: str, piloto_id: str) -> dict:
        """Cancela a candidatura de um piloto para uma equipe em uma etapa"""
        try:
            conn = self._get_conn()
            cursor = conn.cursor(dictionary=True)
            
            # 1. Obter dados do candidato
            cursor.execute('''
                SELECT etapa_id, equipe_id, piloto_id, status FROM candidatos_piloto_etapa
                WHERE id = %s
            ''', (candidato_id,))
            
            candidato = cursor.fetchone()
            if not candidato:
                cursor.close()
                conn.close()
                return {'sucesso': False, 'erro': 'Candidatura não encontrada'}
            
            # Verificar se o piloto que está cancelando é o mesmo que se candidatou
            if candidato['piloto_id'] != piloto_id:
                cursor.close()
                conn.close()
                return {'sucesso': False, 'erro': 'Você não pode cancelar a candidatura de outro piloto'}
            
            # Não permitir cancelar se já foi designado
            if candidato['status'] == 'designado':
                cursor.close()
                conn.close()
                return {'sucesso': False, 'erro': 'Não é possível cancelar uma candidatura já designada. Entre em contato com o admin.'}
            
            # 2. Deletar a candidatura
            cursor.execute('''
                DELETE FROM candidatos_piloto_etapa
                WHERE id = %s
            ''', (candidato_id,))
            
            conn.commit()
            cursor.close()
            conn.close()
            
            print(f"[DB] ✓ Candidatura cancelada para piloto {piloto_id}")
            return {'sucesso': True, 'mensagem': 'Candidatura cancelada com sucesso'}
        except Exception as e:
            print(f"[DB] Erro ao cancelar candidatura: {e}")
            import traceback
            traceback.print_exc()
            return {'sucesso': False, 'erro': str(e)}

    def obter_pilotos_para_confirmacao(self, etapa_id: str) -> dict:
        """Retorna pilotos que precisam confirmar participação (candidatos e alocados)"""
        try:
            conn = self._get_conn()
            cursor = conn.cursor(dictionary=True)
            
            # Buscar etapa
            cursor.execute('''
                SELECT id, data_etapa, hora_etapa FROM etapas
                WHERE id = %s
            ''', (etapa_id,))
            
            etapa = cursor.fetchone()
            if not etapa:
                cursor.close()
                conn.close()
                return {'sucesso': False, 'erro': 'Etapa não encontrada'}
            
            # Buscar candidatos (podem ser só candidatos ou já alocados)
            # Candidatos em candidatos_piloto_etapa
            cursor.execute('''
                SELECT 
                    cpe.id as candidato_id,
                    NULL as participacao_id,
                    cpe.piloto_id,
                    pi.nome as piloto_nome,
                    cpe.equipe_id,
                    e.nome as equipe_nome,
                    cpe.status,
                    'candidato' as tipo
                FROM candidatos_piloto_etapa cpe
                INNER JOIN pilotos pi ON cpe.piloto_id = pi.id
                INNER JOIN equipes e ON cpe.equipe_id = e.id
                WHERE cpe.etapa_id = %s 
                  AND cpe.status IN ('pendente', 'designado', 'confirmado')
                UNION ALL
                SELECT 
                    NULL as candidato_id,
                    pe.id as participacao_id,
                    pe.piloto_id,
                    pi.nome as piloto_nome,
                    pe.equipe_id,
                    e.nome as equipe_nome,
                    pe.status,
                    'alocado' as tipo
                FROM participacoes_etapas pe
                INNER JOIN pilotos pi ON pe.piloto_id = pi.id
                INNER JOIN equipes e ON pe.equipe_id = e.id
                WHERE pe.etapa_id = %s 
                  AND pe.piloto_id IS NOT NULL 
                  AND pe.status IN ('inscrita', 'pendente', 'confirmado')
                ORDER BY piloto_nome ASC
            ''', (etapa_id, etapa_id))
            
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
            
            print(f"[DB] ✓ Piloto {piloto_id} confirmou participação")
            return {'sucesso': True, 'mensagem': 'Participação confirmada com sucesso'}
        except Exception as e:
            print(f"[DB] Erro ao confirmar participação: {e}")
            import traceback
            traceback.print_exc()
            return {'sucesso': False, 'erro': str(e)}

    def confirmar_candidatura_piloto_etapa(self, candidato_id: str, piloto_id: str) -> dict:
        """Piloto confirma que vai andar (confirmação de candidatura)"""
        try:
            conn = self._get_conn()
            cursor = conn.cursor(dictionary=True)
            
            # Verificar se candidatura existe
            cursor.execute('''
                SELECT etapa_id, equipe_id, piloto_id, status FROM candidatos_piloto_etapa
                WHERE id = %s
            ''', (candidato_id,))
            
            candidatura = cursor.fetchone()
            if not candidatura:
                cursor.close()
                conn.close()
                return {'sucesso': False, 'erro': 'Candidatura não encontrada'}
            
            # Verificar se piloto é o correto
            if candidatura['piloto_id'] != piloto_id:
                cursor.close()
                conn.close()
                return {'sucesso': False, 'erro': 'Piloto não autorizado'}
            
            # Atualizar status para 'confirmado'
            cursor.execute('''
                UPDATE candidatos_piloto_etapa
                SET status = 'confirmado'
                WHERE id = %s
            ''', (candidato_id,))
            
            conn.commit()
            cursor.close()
            conn.close()
            
            print(f"[DB] ✓ Piloto {piloto_id} confirmou candidatura")
            return {'sucesso': True, 'mensagem': 'Candidatura confirmada com sucesso'}
        except Exception as e:
            print(f"[DB] Erro ao confirmar candidatura: {e}")
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
            novo_piloto_id = None
            
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
            return {'sucesso': True, 'mensagem': mensagem, 'proximo_piloto': novo_piloto_id}
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
                    COALESCE(e.nome, 'N/A') as equipe_nome
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
            
            return {
                'sucesso': True,
                'pilotos': pilotos or [],
                'total': len(pilotos or [])
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