# Configuração do MySQL para Imagens Grandes

## Problema
As imagens de carros e peças podem exceder o limite padrão `max_allowed_packet` do MySQL.

**Erro**: `Got a packet bigger than 'max_allowed_packet' bytes`

## Solução 1: Aumentar max_allowed_packet (Recomendado)

O sistema agora comprime automaticamente imagens maiores que 500KB, mas para máxima compatibilidade, aumente o limite do MySQL:

### Windows (MySQL como Serviço)

1. Localize o arquivo `my.ini` (normalmente em `C:\ProgramData\MySQL\MySQL Server 8.0\my.ini`)

2. Adicione ou modifique a linha `max_allowed_packet`:
   ```ini
   [mysqld]
   max_allowed_packet = 100M
   ```

3. Reinicie o serviço MySQL:
   ```bash
   net stop MySQL80
   net start MySQL80
   ```

### Linux/Mac (MySQL via Homebrew ou apt-get)

1. Edite `/etc/mysql/my.cnf` ou `/etc/mysql/mysql.conf.d/mysqld.cnf`

2. Adicione ou modifique:
   ```ini
   [mysqld]
   max_allowed_packet = 100M
   ```

3. Reinicie o MySQL:
   ```bash
   sudo systemctl restart mysql
   ```

### Verificar o Valor Atual

```sql
SHOW VARIABLES LIKE 'max_allowed_packet';
```

### Mudar Temporariamente (durante a sessão)

```sql
SET GLOBAL max_allowed_packet = 100*1024*1024;  -- 100MB
```

## Solução 2: Compressão Automática (Implementada)

O sistema agora comprime automaticamente:
- Imagens **maiores que 500KB** são redimensionadas para máx 1920x1920px
- Qualidade JPEG reduzida para 70% (ainda mantém boa qualidade visual)
- Isto reduz ~1.3MB para ~200-300KB

## Recomendações

1. **Imagens para Upload**: Use imagens otimizadas (máx 2-3MB antes do upload)
2. **Limite MySQL**: Configure para pelo menos 50-100MB
3. **Dimensões**: Imagens com ~2000x2000px funcionam melhor

## Teste

Para verificar se tudo está funcionando:

```bash
# Terminal ou PowerShell
mysql -u root -p -e "SHOW VARIABLES LIKE 'max_allowed_packet';"
```

Esperado: `max_allowed_packet | 104857600` (ou maior)
