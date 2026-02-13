-- Script para criar 10 equipes, 10 pilotos e simular cenário de múltiplas candidaturas
USE granpix;

-- ===== 1. CRIAR CAMPEONATO =====
INSERT INTO campeonatos (id, nome, descricao, serie, numero_etapas, status) 
VALUES ('campeonato_teste', 'Campeonato Teste', 'Para teste de candidaturas', 'A1', 1, 'ativo');

-- ===== 2. CRIAR ETAPA =====
INSERT INTO etapas (id, campeonato_id, numero, nome, descricao, data_etapa, hora_etapa, serie, status) 
VALUES ('etapa_teste', 'campeonato_teste', 1, 'Etapa de Teste', 'Etapa para teste de múltiplas candidaturas', DATE_ADD(CURDATE(), INTERVAL 1 DAY), '14:00:00', 'A1', 'agendada');

-- ===== 3. CRIAR 10 PILOTOS =====
INSERT INTO pilotos (id, nome, senha_hash) VALUES
('piloto_1', 'Piloto Teste 1', SHA2('senha123', 256)),
('piloto_2', 'Piloto Teste 2', SHA2('senha123', 256)),
('piloto_3', 'Piloto Teste 3', SHA2('senha123', 256)),
('piloto_4', 'Piloto Teste 4', SHA2('senha123', 256)),
('piloto_5', 'Piloto Teste 5', SHA2('senha123', 256)),
('piloto_6', 'Piloto Teste 6', SHA2('senha123', 256)),
('piloto_7', 'Piloto Teste 7', SHA2('senha123', 256)),
('piloto_8', 'Piloto Teste 8', SHA2('senha123', 256)),
('piloto_9', 'Piloto Teste 9', SHA2('senha123', 256)),
('piloto_10', 'Piloto Teste 10', SHA2('senha123', 256));

-- ===== 4. CRIAR 10 EQUIPES COM CARROS =====
INSERT INTO equipes (id, nome, senha_hash, saldo) VALUES
('equipe_1', 'Equipe Teste 1', SHA2('senha123', 256), 1000000),
('equipe_2', 'Equipe Teste 2', SHA2('senha123', 256), 1000000),
('equipe_3', 'Equipe Teste 3', SHA2('senha123', 256), 1000000),
('equipe_4', 'Equipe Teste 4', SHA2('senha123', 256), 1000000),
('equipe_5', 'Equipe Teste 5', SHA2('senha123', 256), 1000000),
('equipe_6', 'Equipe Teste 6', SHA2('senha123', 256), 1000000),
('equipe_7', 'Equipe Teste 7', SHA2('senha123', 256), 1000000),
('equipe_8', 'Equipe Teste 8', SHA2('senha123', 256), 1000000),
('equipe_9', 'Equipe Teste 9', SHA2('senha123', 256), 1000000),
('equipe_10', 'Equipe Teste 10', SHA2('senha123', 256), 1000000);

-- ===== 5. CRIAR CARROS PARA CADA EQUIPE =====
INSERT INTO carros (id, equipe_id, nome, modelo, placa, ano, serie) VALUES
('carro_1', 'equipe_1', 'Carro Teste 1', 'Modelo X', 'ABC1001', 2023, 'A1'),
('carro_2', 'equipe_2', 'Carro Teste 2', 'Modelo X', 'ABC1002', 2023, 'A1'),
('carro_3', 'equipe_3', 'Carro Teste 3', 'Modelo X', 'ABC1003', 2023, 'A1'),
('carro_4', 'equipe_4', 'Carro Teste 4', 'Modelo X', 'ABC1004', 2023, 'A1'),
('carro_5', 'equipe_5', 'Carro Teste 5', 'Modelo X', 'ABC1005', 2023, 'A1'),
('carro_6', 'equipe_6', 'Carro Teste 6', 'Modelo X', 'ABC1006', 2023, 'A1'),
('carro_7', 'equipe_7', 'Carro Teste 7', 'Modelo X', 'ABC1007', 2023, 'A1'),
('carro_8', 'equipe_8', 'Carro Teste 8', 'Modelo X', 'ABC1008', 2023, 'A1'),
('carro_9', 'equipe_9', 'Carro Teste 9', 'Modelo X', 'ABC1009', 2023, 'A1'),
('carro_10', 'equipe_10', 'Carro Teste 10', 'Modelo X', 'ABC1010', 2023, 'A1');

-- ===== 6. INSCREVER EQUIPES NA ETAPA (tipo: precisa_piloto) =====
INSERT INTO participacoes_etapas (id, etapa_id, equipe_id, carro_id, piloto_id, tipo_participacao, status) VALUES
('part_1', 'etapa_teste', 'equipe_1', 'carro_1', NULL, 'precisa_piloto', 'sem_piloto'),
('part_2', 'etapa_teste', 'equipe_2', 'carro_2', NULL, 'precisa_piloto', 'sem_piloto'),
('part_3', 'etapa_teste', 'equipe_3', 'carro_3', NULL, 'precisa_piloto', 'sem_piloto'),
('part_4', 'etapa_teste', 'equipe_4', 'carro_4', NULL, 'precisa_piloto', 'sem_piloto'),
('part_5', 'etapa_teste', 'equipe_5', 'carro_5', NULL, 'precisa_piloto', 'sem_piloto'),
('part_6', 'etapa_teste', 'equipe_6', 'carro_6', NULL, 'precisa_piloto', 'sem_piloto'),
('part_7', 'etapa_teste', 'equipe_7', 'carro_7', NULL, 'precisa_piloto', 'sem_piloto'),
('part_8', 'etapa_teste', 'equipe_8', 'carro_8', NULL, 'precisa_piloto', 'sem_piloto'),
('part_9', 'etapa_teste', 'equipe_9', 'carro_9', NULL, 'precisa_piloto', 'sem_piloto'),
('part_10', 'etapa_teste', 'equipe_10', 'carro_10', NULL, 'precisa_piloto', 'sem_piloto');

-- ===== 7. CANDIDATURAS: Pilotos 1-5 para Equipe 1 =====
INSERT INTO candidatos_piloto_etapa (id, etapa_id, equipe_id, piloto_id, status, data_inscricao) VALUES
(UUID(), 'etapa_teste', 'equipe_1', 'piloto_1', 'pendente', NOW()),
(UUID(), 'etapa_teste', 'equipe_1', 'piloto_2', 'pendente', NOW()),
(UUID(), 'etapa_teste', 'equipe_1', 'piloto_3', 'pendente', NOW()),
(UUID(), 'etapa_teste', 'equipe_1', 'piloto_4', 'pendente', NOW()),
(UUID(), 'etapa_teste', 'equipe_1', 'piloto_5', 'pendente', NOW());

-- ===== 8. CANDIDATURAS: Pilotos 6-10 para Equipes 2-10 (1 por equipe) =====
INSERT INTO candidatos_piloto_etapa (id, etapa_id, equipe_id, piloto_id, status, data_inscricao) VALUES
(UUID(), 'etapa_teste', 'equipe_2', 'piloto_6', 'pendente', NOW()),
(UUID(), 'etapa_teste', 'equipe_3', 'piloto_7', 'pendente', NOW()),
(UUID(), 'etapa_teste', 'equipe_4', 'piloto_8', 'pendente', NOW()),
(UUID(), 'etapa_teste', 'equipe_5', 'piloto_9', 'pendente', NOW()),
(UUID(), 'etapa_teste', 'equipe_6', 'piloto_10', 'pendente', NOW());

-- ===== QUERY PARA VER O ESTADO FINAL =====
SELECT 'Pilotos' as tipo, COUNT(*) as quantidade FROM pilotos WHERE id LIKE 'piloto_%'
UNION ALL
SELECT 'Equipes', COUNT(*) FROM equipes WHERE id LIKE 'equipe_%'
UNION ALL
SELECT 'Carros', COUNT(*) FROM carros WHERE id LIKE 'carro_%'
UNION ALL
SELECT 'Candidaturas', COUNT(*) FROM candidatos_piloto_etapa WHERE etapa_id = 'etapa_teste';

-- Ver candidaturas por equipe
SELECT 
    CONCAT('Equipe Teste ', SUBSTR(e.id, 7)) as equipe,
    COUNT(*) as candidatos,
    GROUP_CONCAT(p.nome SEPARATOR ', ') as pilotos
FROM candidatos_piloto_etapa c
JOIN equipes e ON c.equipe_id = e.id
JOIN pilotos p ON c.piloto_id = p.id
WHERE c.etapa_id = 'etapa_teste'
GROUP BY c.equipe_id
ORDER BY e.id;
