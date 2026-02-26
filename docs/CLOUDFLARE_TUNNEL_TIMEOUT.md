# Cloudflare Tunnel – Timeout no Quick Tunnel

---

## Só quero expor o app de graça, sem domínio

Se você **não quer usar domínio** e só precisa de um link público **grátis** para acessar o app (tipo `https://alguma-coisa.random.com`):

### Opção A: Cloudflare Quick Tunnel (sem conta)

Com o app rodando na porta 5000 (`python app.py`), em **outro terminal**:

```powershell
cloudflared tunnel --url http://localhost:5000
```

Se aparecer uma URL `https://xxxx.trycloudflare.com`, use essa. Se der **timeout**, teste em outra rede (ex.: celular em hotspot) ou use a Opção B ou C abaixo.

### Opção B: ngrok (grátis, estável)

1. Crie conta grátis em https://ngrok.com e baixe o ngrok para Windows.
2. Descompacte e, no PowerShell (na pasta do ngrok):
   ```powershell
   .\ngrok.exe http 5000
   ```
3. Use a URL `https://xxxx.ngrok-free.app` que aparecer. Não precisa de domínio.

### Opção C: localhost.run (grátis, sem instalar nada)

Se você tem **OpenSSH** no Windows (Windows 10/11 costuma ter):

```powershell
ssh -R 80:localhost:5000 nokey@localhost.run
```

Ele mostra uma URL pública (ex.: `https://xxxx.lhr.life`). Não precisa de conta nem instalar outro programa.

---

Se aparecer (no Cloudflare quick tunnel):
```text
failed to request quick Tunnel: Post "https://api.trycloudflare.com/tunnel": context deadline exceeded (Client.Timeout exceeded while awaiting headers)
```

o `cloudflared` não está conseguindo alcançar `api.trycloudflare.com`. Use uma das opções abaixo.

---

## 1. Verificar rede e firewall

- **Firewall / antivírus:** libere o `cloudflared` ou teste desativando por um momento.
- **Proxy:** se usar proxy corporativo, configure:
  ```powershell
  $env:HTTPS_PROXY = "http://proxy:porta"
  $env:HTTP_PROXY  = "http://proxy:porta"
  ```
  Ou rode o tunnel em outra rede (ex.: celular em modo hotspot).
- **Teste de conectividade:**
  ```powershell
  Test-NetConnection api.trycloudflare.com -Port 443
  ```
  Ou no navegador: https://api.trycloudflare.com (pode retornar 404; o importante é não dar timeout).

---

## 2. Aumentar timeout (quick tunnel)

Às vezes a API responde devagar. Tente dar mais tempo:

```powershell
cloudflared tunnel --url http://localhost:5000 --no-autoupdate
```

Se a sua versão aceitar variável de timeout (depende da versão):

```powershell
$env:CF_QUICK_TUNNEL_TIMEOUT = "60"
cloudflared tunnel --url http://localhost:5000
```

---

## 3. Usar túnel nomeado (recomendado – não usa trycloudflare.com)

O quick tunnel depende de `api.trycloudflare.com`. O **túnel nomeado** usa a API normal do Cloudflare (outros endpoints), que costuma ser mais estável e é o indicado para produção.

### Passo a passo (Windows)

1. **Conta Cloudflare**  
   Crie em https://dash.cloudflare.com se ainda não tiver.

2. **Login do cloudflared (obrigatório primeiro)**
   ```powershell
   cloudflared tunnel login
   ```
   Abre o navegador; escolha o domínio e autorize. Isso gera o **certificado de origem** `cert.pem` em `%USERPROFILE%\.cloudflared\`. Sem esse arquivo o `tunnel run` falha com erro de "origin certificate".

3. **Criar o túnel**
   ```powershell
   cloudflared tunnel create granpix
   ```
   Anote o **UUID** que aparecer (ex.: `abcd1234-5678-...`). Será criado um arquivo `<UUID>.json` na mesma pasta `.cloudflared`.

4. **Configurar o túnel**  
   Crie ou edite o arquivo `%USERPROFILE%\.cloudflared\config.yml` (no Windows: `C:\Users\SEU_USUARIO\.cloudflared\config.yml`). Exemplo:

   ```yaml
   tunnel: granpix
   origincert: C:\Users\Gustavo Marquardt\.cloudflared\cert.pem
   credentials-file: C:\Users\Gustavo Marquardt\.cloudflared\<UUID>.json

   ingress:
     - hostname: granpix.seudominio.com
       service: http://localhost:5000
     - service: http_status:404
   ```

   **Ajuste:**
   - **origincert:** caminho completo do `cert.pem` (gerado pelo `tunnel login`). Use seu usuário Windows no caminho.
   - **credentials-file:** caminho do arquivo `.json` do túnel (o UUID que apareceu no `tunnel create`).
   - **hostname:** subdomínio do seu domínio no Cloudflare (ex.: `granpix.seudominio.com`).

5. **Registrar o hostname no DNS**  
   No Dashboard: **Zero Trust** → **Networks** → **Tunnels** → **granpix** → **Public Hostname** → Add:
   - Subdomain: `granpix` (ou o que quiser)
   - Domain: seu domínio
   - Service: **HTTP**, **localhost:5000**

   Ou pela CLI (substitua o hostname):
   ```powershell
   cloudflared tunnel route dns granpix granpix.seudominio.com
   ```

6. **Subir o app e o túnel**  
   Em um terminal:
   ```powershell
   cd "C:\Users\Gustavo Marquardt\OneDrive\Documentos\GRANPIX"
   python app.py
   ```
   Em outro:
   ```powershell
   cloudflared tunnel run granpix
   ```

Acesse **https://granpix.seudominio.com** (ou o hostname que configurou). Esse fluxo **não usa** `api.trycloudflare.com`, então o timeout do quick tunnel deixa de ser um problema.

---

## 4. Se não tiver domínio no Cloudflare

- Compre ou transfira um domínio para o Cloudflare, ou  
- Use um subdomínio de um serviço que dê domínio (ex.: alguns planos de tunnel/DDNS).  

O quick tunnel (`trycloudflare.com`) é a única opção “sem conta/domínio”; se ele continuar em timeout, a solução estável é criar conta + túnel nomeado (itens acima).

---

## 5. Erro: "Cannot determine default origin certificate path"

Se aparecer:
```text
Cannot determine default origin certificate path. No file cert.pem in [~/.cloudflared ...]
error parsing tunnel ID: Error locating origin cert: client didn't specify origincert path
```

**Causa:** o `cloudflared` não encontra o certificado de origem (`cert.pem`). No Windows a pasta padrão às vezes não é detectada.

**Solução:**

1. Gerar o certificado (se ainda não fez): `cloudflared tunnel login` — escolha o domínio no navegador. Deve ser criado `C:\Users\Gustavo Marquardt\.cloudflared\cert.pem`.

2. Abrir o config e colocar o caminho completo do `cert.pem`:
   ```powershell
   notepad $env:USERPROFILE\.cloudflared\config.yml
   ```
   Inclua a linha **origincert** (troque o usuário se for diferente):
   ```yaml
   tunnel: granpix
   origincert: C:\Users\Gustavo Marquardt\.cloudflared\cert.pem
   credentials-file: C:\Users\Gustavo Marquardt\.cloudflared\SEU-UUID-AQUI.json

   ingress:
     - hostname: granpix.seudominio.com
       service: http://localhost:5000
     - service: http_status:404
   ```
   Substitua `SEU-UUID-AQUI.json` pelo nome real do arquivo `.json` que está na pasta `.cloudflared`.

3. Rodar de novo: `cloudflared tunnel run granpix`.

4. Conferir arquivos: `Get-ChildItem $env:USERPROFILE\.cloudflared` — deve listar `cert.pem` e um `*.json`.
