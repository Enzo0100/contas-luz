FROM python:3.11-slim

WORKDIR /app

# Instalar dependências do sistema
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    libpq-dev \
    libtesseract-dev \
    tesseract-ocr \
    tesseract-ocr-por \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Instalar dependências do Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Criar estrutura de diretórios
RUN mkdir -p /app/data/raw \
    /app/data/processed \
    /app/data/faiss_index \
    /app/data/embeddings_cache \
    /app/logs

# Copiar código da aplicação
COPY app/ /app/app/
COPY scripts/ /app/scripts/

# Definir variáveis de ambiente padrão
ENV PYTHONPATH=/app \
    DATA_DIR=/app/data \
    LOGS_DIR=/app/logs \
    DIRETORIO_DADOS=/app/data/processed \
    DIRETORIO_FAISS=/app/data/faiss_index \
    HOST=0.0.0.0 \
    PORT=8000 \
    DEBUG=False \
    LOG_LEVEL=INFO

# Expor a porta da API
EXPOSE 8000

# Comando para iniciar a aplicação
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]