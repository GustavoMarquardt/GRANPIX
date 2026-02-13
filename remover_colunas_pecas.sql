-- Script para remover as colunas de peças da tabela carros
-- As peças agora são referenciadas apenas pela tabela 'pecas' com carro_id

ALTER TABLE carros DROP COLUMN motor_id;
ALTER TABLE carros DROP COLUMN cambio_id;
ALTER TABLE carros DROP COLUMN suspensao_id;
ALTER TABLE carros DROP COLUMN kit_angulo_id;
ALTER TABLE carros DROP COLUMN diferencial_id;
