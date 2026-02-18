# GRANPIX em Docker

O projeto pode rodar totalmente em containers: aplicação Flask + MariaDB, sem precisar instalar MySQL/MariaDB na máquina.

## Se a imagem ficar desatualizada (ex.: erro de collation ou "Aborted connection")

Forçar reconstrução **completa** da imagem (remove a imagem antiga e reconstrói):

```powershell
docker compose down
docker rmi granpix-app:latest
docker compose build --no-cache app
docker compose up -d
```

Depois confira os logs do app. Você deve ver:
- `[APP] Conectando ao banco (PyMySQL)...`
- `[APP] Banco inicializado.`

Se aparecer `Conectando ao banco (PyMySQL)...` e em seguida erro, o problema é outro. Se essa linha **não** aparecer, a imagem ainda é a antiga — use os comandos acima e garanta que `docker rmi granpix-app:latest` foi executado.

## Pré-requisitos

- [Docker](https://docs.docker.com/get-docker/) (Desktop ou Engine)
- [Docker Compose](https://docs.docker.com/compose/install/) (já incluso no Docker Desktop)

## Subir o sistema

Na pasta do projeto:

```bash
docker compose up -d
```

Na primeira vez, a imagem da aplicação será construída e o banco será criado. O app só inicia depois que o MariaDB estiver aceitando conexões (script `wait_for_db.py`).

## Acesso

- **Aplicação:** http://localhost:5000
- **Banco (opcional):** porta **3307** no host (evita conflito com MySQL/MariaDB local na 3306). Use qualquer cliente MySQL (DBeaver, HeidiSQL, etc.) com:
  - Host: `localhost`
  - Porta: `3307`
  - Usuário: `root`
  - Senha: `granpix`
  - Banco: `granpix`

## Comandos úteis

```bash
# Ver logs da aplicação
docker compose logs -f app

# Ver logs do banco
docker compose logs -f db

# Parar tudo
docker compose down

# Parar e remover volumes (apaga dados do banco)
docker compose down -v
```

## Variáveis de ambiente (docker-compose)

No `docker-compose.yml` o app usa:

| Variável        | Valor no container   | Descrição                          |
|-----------------|----------------------|------------------------------------|
| `MYSQL_CONFIG`  | `mysql://root:granpix@db:3306/granpix` | Conexão com o MariaDB do container |
| `FLASK_RUN_HOST` | `0.0.0.0`            | Para aceitar conexões de fora do container |
| `FLASK_DEBUG`   | `false`              | Desativa reloader em produção      |
| `WAIT_HOST`    | `db`                 | Serviço do banco para o script de espera |

Para alterar a senha do root do MariaDB, mude `MARIADB_ROOT_PASSWORD` no serviço `db` e o valor de `MYSQL_CONFIG` no serviço `app` (ex.: `mysql://root:SUA_SENHA@db:3306/granpix`).

## Desenvolvimento com volume

Para editar o código e ver mudanças sem reconstruir a imagem, no `docker-compose.yml` descomente o volume do serviço `app`:

```yaml
volumes:
  - .:/app
```

Reinicie: `docker compose up -d --build`. O reloader do Flask não está ativo por padrão (`FLASK_DEBUG=false`); para ativar, altere para `FLASK_DEBUG: "true"` no `docker-compose.yml`.
