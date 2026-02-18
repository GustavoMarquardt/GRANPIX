# GRANPIX - imagem da aplicação Flask
FROM python:3.12-slim

WORKDIR /app

# mysql-connector-python é puro Python; sem dependências de sistema extras

# Copiar e instalar dependências Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar código (src/database.py deve estar sem charset no connect, compatível com MariaDB)
COPY src/database.py src/database.py
COPY . .

# Porta exposta
EXPOSE 5000

# Entrypoint: espera o banco e inicia a aplicação (Python evita problemas de CRLF no Windows)
ENTRYPOINT ["python", "docker-entrypoint.py"]
CMD ["python", "app.py"]
