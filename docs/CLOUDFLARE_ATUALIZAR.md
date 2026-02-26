# Atualizar produção com Cloudflare

O código atual já está no GitHub (branch `lord`). Escolha o cenário que combina com seu uso do Cloudflare.

---

## Cenário 1: Cloudflare na frente de um servidor (proxy/CDN)

O app Flask roda em um VPS/servidor e o Cloudflare faz proxy (DNS + cache). Para colocar o **código atual** em produção:

### No servidor onde o app roda

1. Acesse o servidor (SSH).
2. Vá até a pasta do projeto e atualize o código:

```bash
cd /caminho/do/GRANPIX   # ajuste o caminho
git fetch origin
git checkout lord
git pull origin lord
```

3. Reinicie o app (ajuste ao seu jeito de rodar):

```bash
# Se usar systemd:
sudo systemctl restart granpix

# Se usar supervisor:
sudo supervisorctl restart granpix

# Se rodar com gunicorn/uwsgi, mate o processo e suba de novo.
```

4. (Opcional) No **Dashboard do Cloudflare**: *Caching* → *Configuration* → **Purge Everything** para limpar o cache e garantir que os usuários vejam a versão nova.

---

## Cenário 2: Cloudflare Pages conectado ao GitHub

Se o projeto no Cloudflare Pages está ligado a este repositório:

- Cada **push** no branch de produção dispara um novo build/deploy.
- O último push no branch `lord` já deve ter gerado um deploy automático.

Para conferir ou forçar um novo deploy:

1. Acesse [Cloudflare Dashboard](https://dash.cloudflare.com) → **Workers & Pages**.
2. Abra o projeto do GRANPIX.
3. Em **Deployments**, veja se o último deploy é do commit mais recente.
4. Se quiser um novo deploy: **Create deployment** ou **Retry deployment** no último commit.

Se o branch de produção no Pages for outro (por exemplo `main`), faça merge do `lord` nesse branch e dê push, ou configure o branch de produção em **Settings** → **Builds & deployments** para usar o `lord`.

---

## Script rápido (servidor)

Na pasta do projeto no servidor você pode usar:

```bash
# Dar permissão uma vez
chmod +x scripts/atualizar_producao.sh

# Rodar para atualizar código e ver instruções de restart
./scripts/atualizar_producao.sh
```

(O script faz `git pull origin lord` e mostra como reiniciar o app.)
