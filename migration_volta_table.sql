-- Criar tabela volta para armazenar voltas dos pilotos
CREATE TABLE IF NOT EXISTS volta (
    id VARCHAR(36) PRIMARY KEY DEFAULT (UUID()),
    id_piloto VARCHAR(36) NOT NULL,
    id_equipe VARCHAR(36) NOT NULL,
    id_etapa VARCHAR(36) NOT NULL,
    nota_linha INT DEFAULT NULL CHECK (nota_linha >= 0 AND nota_linha <= 40),
    nota_angulo INT DEFAULT NULL CHECK (nota_angulo >= 0 AND nota_angulo <= 30),
    nota_estilo INT DEFAULT NULL CHECK (nota_estilo >= 0 AND nota_estilo <= 30),
    status ENUM('agendada', 'em_andamento', 'finalizada') DEFAULT 'agendada',
    data_criacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    data_atualizacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    UNIQUE KEY unique_volta (id_piloto, id_equipe, id_etapa),
    FOREIGN KEY (id_piloto) REFERENCES pilotos(id),
    FOREIGN KEY (id_equipe) REFERENCES equipes(id),
    FOREIGN KEY (id_etapa) REFERENCES etapas(id),
    
    INDEX idx_etapa (id_etapa),
    INDEX idx_equipe (id_equipe),
    INDEX idx_piloto (id_piloto),
    INDEX idx_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Remover tabela etapa_notas antiga (se quiser, pode comentar)
-- DROP TABLE IF EXISTS etapa_notas;
