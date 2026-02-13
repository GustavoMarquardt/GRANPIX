-- Criar tabela para armazenar notas das equipes por etapa
CREATE TABLE IF NOT EXISTS etapa_notas (
    id VARCHAR(36) PRIMARY KEY DEFAULT (UUID()),
    etapa_id VARCHAR(36) NOT NULL,
    equipe_id VARCHAR(36) NOT NULL,
    nota_linha INT DEFAULT 0 COMMENT 'Nota de linha (0-40)',
    nota_angulo INT DEFAULT 0 COMMENT 'Nota de ângulo (0-30)',
    nota_estilo INT DEFAULT 0 COMMENT 'Nota de estilo (0-30)',
    data_criacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    data_atualizacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY unique_etapa_equipe (etapa_id, equipe_id),
    FOREIGN KEY (etapa_id) REFERENCES etapas(id) ON DELETE CASCADE,
    FOREIGN KEY (equipe_id) REFERENCES equipes(id) ON DELETE CASCADE,
    INDEX idx_etapa_id (etapa_id),
    INDEX idx_equipe_id (equipe_id)
);

COMMIT;
