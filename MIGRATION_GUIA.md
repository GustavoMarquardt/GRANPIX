# Guia para Executar a Migration de Remover Colunas

## Problema
A tabela `carros` possui colunas redundantes (`motor_id`, `cambio_id`, `suspensao_id`, `kit_angulo_id`, `diferencial_id`) que não devem mais existir, pois a referência agora é feita através da tabela `pecas` com o campo `carro_id`.

## Solução
Execute o arquivo SQL: `migration_remove_colunas_carros.sql`

---

## Opção 1: phpMyAdmin (mais fácil)

1. Acesse phpMyAdmin (geralmente em `http://localhost/phpmyadmin`)
2. Selecione o banco de dados `granpix`
3. Vá para a aba **SQL**
4. Copie e cole o conteúdo de `migration_remove_colunas_carros.sql`
5. Clique em **Executar**

---

## Opção 2: MySQL Workbench

1. Abra MySQL Workbench
2. Conecte-se ao servidor MySQL
3. Abra o arquivo `migration_remove_colunas_carros.sql` (File → Open SQL Script)
4. Clique em **Execute** (ou Ctrl+Enter)

---

## Opção 3: Linha de Comando MySQL

```bash
# Windows
mysql -u root -p granpix < migration_remove_colunas_carros.sql

# Linux/Mac
mysql -u root -p granpix < migration_remove_colunas_carros.sql

# Com arquivo SQL em outro caminho:
cd C:\Users\Gustavo Marquardt\Documents\GRANPIX
mysql -u root -p granpix < migration_remove_colunas_carros.sql
```

---

## Verificação Pós-Execução

Para verificar se a migration foi bem-sucedida:

### Via phpMyAdmin:
1. Vá para a tabela `carros`
2. Clique em **Estrutura**
3. Confirme que as 5 colunas foram removidas

### Via SQL:
```sql
-- Verificar colunas da tabela carros
DESCRIBE carros;

-- Ou:
SELECT COLUMN_NAME 
FROM INFORMATION_SCHEMA.COLUMNS 
WHERE TABLE_NAME='carros' 
ORDER BY COLUMN_NAME;
```

### Via Python:
```python
from src.database import DatabaseManager

db = DatabaseManager()
conn = db._get_conn()
cursor = conn.cursor()

# Listar colunas da tabela carros
cursor.execute("DESCRIBE carros")
colunas = cursor.fetchall()

print("Colunas da tabela carros:")
for coluna in colunas:
    print(f"  - {coluna[0]} ({coluna[1]})")

cursor.close()
conn.close()
```

---

## O que Mudará

**Antes:**
```
carros.id
carros.motor_id      ← Será removida
carros.cambio_id     ← Será removida
carros.suspensao_id  ← Será removida
carros.kit_angulo_id ← Será removida
carros.diferencial_id ← Será removida
carros.equipe_id
...
```

**Depois:**
```
carros.id
carros.numero_carro
carros.marca
carros.modelo
carros.batidas_totais
carros.vitoria
carros.derrotas
carros.empates
carros.equipe_id
carros.data_criacao
carros.status
...
```

---

## Referência: Novo Sistema de Peças

A partir de agora, peças são gerenciadas assim:

```sql
-- Exemplo: Consultar todas as peças de um carro
SELECT 
    p.id,
    p.nome,
    p.tipo,
    p.instalado,
    p.pix_id,
    c.marca,
    c.modelo
FROM pecas p
JOIN carros c ON p.carro_id = c.id
WHERE p.carro_id = 'UUID_DO_CARRO'
ORDER BY p.tipo;
```

---

## Precaução

⚠️ **Esta operação é irreversível!** Faça backup do banco antes de executar.

```sql
-- Para backup (execute ANTES da migration):
-- Consulte a documentação do seu servidor MySQL
```
