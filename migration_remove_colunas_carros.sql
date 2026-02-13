-- ===============================================================================
-- MIGRATION: Remover colunas redundantes da tabela CARROS
-- ===============================================================================
-- 
-- OBJETIVO: Remover colunas que antes armazenavam IDs de peças específicas
--           agora que temos a tabela PECAS com carro_id para fazer referência
--
-- COLUNAS A REMOVER:
--   - motor_id
--   - cambio_id
--   - suspensao_id
--   - kit_angulo_id
--   - diferencial_id
--
-- A tabela PECAS agora mantém o relacionamento com a tabela CARROS via:
--   - pecas.carro_id (FK para carros.id)
--   - pecas.instalado (1 = instalada, 0 = não instalada)
--   - pecas.tipo (motor, cambio, suspensao, kit_angulo, diferencial, etc)
--
-- ===============================================================================

USE granpix;

-- Verificar se as colunas existem antes de remover
ALTER TABLE carros DROP COLUMN IF EXISTS motor_id;
ALTER TABLE carros DROP COLUMN IF EXISTS cambio_id;
ALTER TABLE carros DROP COLUMN IF EXISTS suspensao_id;
ALTER TABLE carros DROP COLUMN IF EXISTS kit_angulo_id;
ALTER TABLE carros DROP COLUMN IF EXISTS diferencial_id;

-- ===============================================================================
-- Verificação final
-- ===============================================================================
-- Para verificar se as colunas foram removidas com sucesso, execute:
-- DESCRIBE carros;
-- ou
-- SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME='carros';

COMMIT;
