-- ============================================================
-- Corrigir: "Host 'localhost' is not allowed to connect"
-- Execute este script no MariaDB/MySQL (linha de comando).
-- ============================================================

-- Permite conexão do usuário root a partir de localhost (sem senha)
CREATE USER IF NOT EXISTS 'root'@'localhost' IDENTIFIED BY '';

-- Permite conexão do usuário root a partir de 127.0.0.1 (sem senha)
CREATE USER IF NOT EXISTS 'root'@'127.0.0.1' IDENTIFIED BY '';

-- Concede todos os privilégios para root@localhost
GRANT ALL PRIVILEGES ON *.* TO 'root'@'localhost' WITH GRANT OPTION;

-- Concede todos os privilégios para root@127.0.0.1
GRANT ALL PRIVILEGES ON *.* TO 'root'@'127.0.0.1' WITH GRANT OPTION;

-- Garante que o banco granpix existe e que root pode usá-lo
CREATE DATABASE IF NOT EXISTS granpix CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
GRANT ALL PRIVILEGES ON granpix.* TO 'root'@'localhost';
GRANT ALL PRIVILEGES ON granpix.* TO 'root'@'127.0.0.1';

-- Aplica as alterações
FLUSH PRIVILEGES;

-- Confirma
SELECT user, host FROM mysql.user WHERE user = 'root';
