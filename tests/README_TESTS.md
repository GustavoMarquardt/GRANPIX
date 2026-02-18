# Testes do GRANPIX

## Instalação

```bash
pip install -r requirements-test.txt
```

## Executar todos os testes

Requer banco MySQL/MariaDB acessível (Docker ou local). O app será importado e conectará ao banco de **testes**.

### Rápido: só testes unitários (sem banco)

```bash
pytest tests/test_units.py tests/test_database_module.py::TestDatabaseManagerParsing -v
```

### Com Docker (recomendado)

1. Suba o stack: `docker compose up -d`
2. Crie o banco de testes (uma vez):

   O banco **granpix_test** é criado automaticamente na primeira vez que os testes rodam (o `DatabaseManager` faz `CREATE DATABASE IF NOT EXISTS` com o nome da URL). Não é necessário criá-lo à mão.

   Se quiser criar manualmente (imagem MariaDB usa o cliente `mariadb`, não `mysql`):

   ```powershell
   docker compose exec db mariadb -u root -pgranpix -e "CREATE DATABASE IF NOT EXISTS granpix_test CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
   ```

3. Rode os testes apontando para o banco no host (porta 3307):

   ```powershell
   $env:TEST_MYSQL_CONFIG = "mysql://root:granpix@127.0.0.1:3307/granpix_test"
   pytest
   ```

### Rodar testes dentro do container (recomendado para validar tudo)

Com o stack no ar (`docker compose up -d`), rode os testes. O banco **granpix_test** é criado automaticamente na primeira conexão:

```powershell
docker compose exec -e TEST_MYSQL_CONFIG=mysql://root:granpix@db:3306/granpix_test app python -m pytest /app/tests -v --tb=short
```

Na imagem MariaDB o cliente é `mariadb` (não `mysql`). Para criar o banco à mão, se precisar:

```powershell
docker compose exec db mariadb -u root -pgranpix -e "CREATE DATABASE IF NOT EXISTS granpix_test CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
```

### Sem Docker (MySQL/MariaDB local)

```powershell
$env:TEST_MYSQL_CONFIG = "mysql://root:SUA_SENHA@127.0.0.1:3306/granpix_test"
pytest
```

Se não definir `TEST_MYSQL_CONFIG`, o padrão é `mysql://root:granpix@127.0.0.1:3307/granpix_test`.

## Comandos úteis

```bash
# Todos os testes
pytest

# Com cobertura
pytest --cov=app --cov=src --cov-report=term-missing

# Apenas testes que não dependem do banco (test_units.py)
pytest tests/test_units.py -v

# Verbose
pytest -v
```

## Estrutura

- `conftest.py`: Define `MYSQL_CONFIG` para testes, importa o app, fornece fixtures `client`, `client_admin`, `client_equipe`. Se o banco não estiver acessível, os testes que dependem do app são pulados.
- `test_units.py`: Testes unitários (regex, etc.) — **não precisam de banco**.
- `test_public_routes.py`: Rotas públicas (/, /login, GET /api/equipes) e login admin.
- `test_api_protected.py`: Rotas que exigem autenticação (401 sem auth, admin session).
- `test_loja_garagem.py`: Loja e garagem (status esperados).
- `test_database_module.py`: DatabaseManager (URL inválida, etc.), só roda se o app tiver carregado.
- `test_admin.py`: Páginas e APIs admin (Cadastrar Carros, Peças, Variações, Equipes, Fazer Etapa, Alocar Pilotos, Comissões); usa fixture `client_admin`. Inclui testes de **persistência**: após cadastrar carro/peça/equipe, verifica que o item aparece na listagem (GET), validando que foi gravado no banco.
- `e2e/`: Testes E2E no navegador (Playwright). Veja abaixo.

## Testes E2E (frontend no navegador)

Testes que abrem um navegador real e acessam o app em **http://localhost:5000**. Úteis para validar o frontend (páginas carregam, formulários existem, etc.).

### Pré-requisitos

1. **App rodando** (em outro terminal):
   - Local: `flask run` ou `python app.py`
   - Docker: `docker compose up -d` (app em http://localhost:5000)

2. **Playwright instalado** (uma vez):
   ```bash
   pip install pytest-playwright
   playwright install
   ```
   (Ou só `pip install -r requirements.txt` e depois `playwright install`.)

### Rodar os testes E2E

```bash
# Só testes E2E (app deve estar rodando em localhost:5000)
pytest tests/e2e/ -v

# Ver o teste na tela e resultado de persistência (navegador abre, prints aparecem)
pytest tests/e2e/ -v -s --headed

# Ou use o script (PowerShell)
.\run_tests_visible.ps1
```

**Persistência em todos os testes:** os testes de API (`test_admin.py`) e o E2E de carro+peça imprimem `PERSISTÊNCIA OK` quando rodam com `-s`. Para ver:

```powershell
# E2E com navegador visível + mensagens de persistência
pytest tests/e2e/ -v -s --headed

# Testes de API que validam persistência (carro/peça/equipe na listagem após cadastro)
pytest tests/test_admin.py -v -s -k persiste
```

Os testes em `tests/e2e/test_frontend_admin.py` cobrem:
- `/admin/carros`: título, formulário (marca, botão Cadastrar), lista de carros
- `/admin/pecas`: título, campo nome da peça
- `/admin/variacoes`: título, seletor de modelo

Para **não** rodar os E2E (ex.: em CI sem navegador): `pytest -m "not e2e"`.

## Teste de equipe (opcional)

Para testes que usam sessão de equipe com um ID real (ex.: comprar), crie uma equipe no banco de testes e informe o ID:

```powershell
$env:TEST_EQUIPE_ID = "uuid-da-equipe-no-granpix_test"
pytest tests/test_api_protected.py -v
```
