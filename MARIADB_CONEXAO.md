# Corrigir conexão MariaDB: "Host 'localhost' is not allowed"

## O que está acontecendo

O MariaDB está recusando conexões do host `localhost`. Isso é configuração de **permissões de usuário** no servidor, não do seu código.

## Como corrigir

### 1. Abrir o MariaDB/MySQL pela linha de comando

Use o cliente que veio com sua instalação:

- **XAMPP:**  
  `C:\xampp\mysql\bin\mysql.exe -u root`
- **Laragon:**  
  `C:\laragon\bin\mysql\mysql-...\bin\mysql.exe -u root`
- **MariaDB instalado separado:**  
  `mysql -u root`  
  (ou `mysql -u root -p` se tiver senha)

Se pedir senha e você não definiu nenhuma, pressione Enter.

### 2. Executar o script SQL

**Opção A – Pelo arquivo:**

```bash
mysql -u root < fix_mariadb_host.sql
```

**Opção B – Colar no console do MySQL:**

Abra `fix_mariadb_host.sql`, copie todo o conteúdo e cole no prompt do MySQL (onde aparece `MariaDB [(none)]>` ou `mysql>`), depois Enter.

### 3. Testar

- **App Python:** `python .\app.py`  
  (o projeto já está configurado para usar `127.0.0.1`.)
- **phpMyAdmin:**  
  No `config.inc.php` do phpMyAdmin, altere o host de `'localhost'` para `'127.0.0.1'` na configuração do servidor, ou use o phpMyAdmin depois de aplicar o script (localhost passará a ser permitido).

### 4. phpMyAdmin: usar 127.0.0.1 em vez de localhost

Assim o phpMyAdmin passa a conectar como `root@127.0.0.1`, que costuma funcionar mesmo quando `localhost` está bloqueado.

Localize o arquivo de configuração do phpMyAdmin (ex.: `C:\xampp\phpMyAdmin\config.inc.php` ou dentro da pasta do Laragon) e altere:

```php
$cfg['Servers'][$i]['host'] = '127.0.0.1';   // era 'localhost'
```

Salve e abra o phpMyAdmin de novo no navegador.

### 5. Se a linha de comando do MySQL ainda não conectar

Algumas instalações permitem conexão só por socket ou por outro usuário. Tente:

```bash
mysql -u root -h 127.0.0.1
```

Se o erro continuar, pode ser que o usuário `root` não exista ou esteja bloqueado; aí será preciso usar o painel do XAMPP/Laragon ou a ferramenta de configuração do MariaDB para criar/ajustar o usuário e o host.
