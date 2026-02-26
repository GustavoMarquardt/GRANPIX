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

---

## Cenário 3: Cloudflare Tunnel (cloudflared) no Windows

Você está usando **cloudflared** com quick tunnel (`cloudflared tunnel --url http://localhost:5000`) para expor o app local na internet.

O erro **"Unable to reach the origin service"** / **"connection refused"** acontece quando o **app Flask não está rodando** na porta 5000. O túnel só encaminha tráfego; quem atende é o seu app.

### Ordem correta (dois terminais)

1. **PowerShell 1** – subir o app na porta 5000:
   ```powershell
   cd "C:\Users\Gustavo Marquardt\OneDrive\Documentos\GRANPIX"
   python app.py
   ```
   Deixe este terminal aberto (você deve ver algo como "Running on http://localhost:5000").

2. **PowerShell 2** – depois que o app estiver no ar, abrir o túnel:
   ```powershell
   cloudflared tunnel --url http://localhost:5000
   ```
   Use a URL que aparecer (ex: `https://....trycloudflare.com`).

Enquanto o app não estiver rodando em `localhost:5000`, o cloudflared continuará retornando "connection refused".

### Script PowerShell (opcional)

Na pasta do projeto você pode rodar:

```powershell
.\scripts\iniciar_tunnel_cloudflare.ps1
```

Esse script abre outra janela com o app e, em seguida, inicia o cloudflared na janela atual.
