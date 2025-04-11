# Arquitetura do Sistema de Consulta de Contas de Luz

## Visão Geral

O sistema de consulta de contas de luz é uma aplicação de Retrieval Augmented Generation (RAG) que permite aos usuários consultar informações sobre suas contas de energia elétrica através de linguagem natural. A aplicação extrai dados de PDFs de contas de luz, estrutura essas informações, gera embeddings vetoriais, e utiliza um índice FAISS para busca eficiente quando responde às consultas dos usuários.

## Componentes Principais

### 1. Camada de Extração de Dados

**Componentes:**
- RagFlow com DeepDocs para OCR
- Processador de estruturação de dados

**Função:**
- Extrair texto e dados dos PDFs de contas de luz
- Estruturar as informações em formato JSON padronizado
- Armazenar os dados processados para uso posterior

**Tecnologias:**
- RagFlow
- DeepDocs OCR
- Python para processamento

### 2. Camada de Embeddings e Indexação

**Componentes:**
- Serviço de Embeddings da OpenAI
- Sistema de Cache de Embeddings
- Indexador FAISS

**Função:**
- Gerar embeddings vetoriais para todos os documentos estruturados
- Manter um cache de embeddings para otimização
- Construir e manter um índice FAISS para busca por similaridade

**Tecnologias:**
- OpenAI API (modelo text-embedding-3-small)
- FAISS (Facebook AI Similarity Search)
- Numpy para manipulação de vetores

### 3. Camada de API e Consulta

**Componentes:**
- API REST com FastAPI
- Sistema de Sessões
- Motor de Chat do RagFlow

**Função:**
- Permitir autenticação por matrícula
- Gerenciar sessões de usuário
- Processar consultas em linguagem natural
- Buscar documentos relevantes via FAISS
- Gerar respostas contextualizadas

**Tecnologias:**
- FastAPI
- RagFlow Chat
- OpenAI API (GPT)

### 4. Camada de Apresentação

**Componentes:**
- Interface Web
- Visualização de Dados

**Função:**
- Fornecer interface amigável para os usuários
- Visualizar dados de consumo e gastos
- Permitir consultas em linguagem natural

**Tecnologias:**
- HTML, CSS, JavaScript
- Chart.js para visualizações

## Diagrama de Arquitetura

```
┌───────────────────┐      ┌─────────────────────┐      ┌──────────────────┐
│                   │      │                     │      │                  │
│  PDFs das Contas  │─────▶│  RagFlow/DeepDocs   │─────▶│  Dados JSON      │
│                   │      │  Extração de Dados  │      │  Estruturados    │
└───────────────────┘      └─────────────────────┘      └──────────────────┘
                                                                 │
                                                                 ▼
┌───────────────────┐      ┌─────────────────────┐      ┌──────────────────┐
│                   │      │                     │      │                  │
│  API OpenAI       │◀────▶│  Geração de         │◀────▶│  Cache de        │
│  Embeddings       │      │  Embeddings         │      │  Embeddings      │
└───────────────────┘      └─────────────────────┘      └──────────────────┘
                                     │
                                     ▼
┌───────────────────┐      ┌─────────────────────┐
│                   │      │                     │
│  Índice FAISS     │◀────▶│  Serviço de Busca   │
│                   │      │  por Similaridade   │
└───────────────────┘      └─────────────────────┘
                                     │
                                     ▼
┌───────────────────┐      ┌─────────────────────┐      ┌──────────────────┐
│                   │      │                     │      │                  │
│  API FastAPI      │◀────▶│  RagFlow Chat       │◀────▶│  API OpenAI      │
│                   │      │  Service            │      │  GPT             │
└───────────────────┘      └─────────────────────┘      └──────────────────┘
          │
          ▼
┌───────────────────┐
│                   │
│  Interface Web    │
│  do Usuário       │
└───────────────────┘
```

## Fluxo de Processamento

1. **Extração e Preparação de Dados**
   - PDFs de contas de luz são processados pelo RagFlow/DeepDocs
   - O texto extraído é processado para criar documentos estruturados
   - Os documentos são salvos como arquivos JSON

2. **Indexação**
   - Para cada documento estruturado, embeddings são gerados
   - Os embeddings são armazenados em cache para uso futuro
   - Um índice FAISS é construído usando esses embeddings

3. **Consulta**
   - O usuário se autentica com sua matrícula
   - Uma consulta em linguagem natural é enviada
   - A consulta é convertida em embedding
   - O índice FAISS encontra documentos similares
   - Os documentos relevantes são usados como contexto
   - O RagFlow Chat gera uma resposta relevante e precisa

## Considerações Técnicas

### Escalabilidade

- O sistema utiliza cache de embeddings para reduzir chamadas à API da OpenAI
- O FAISS permite buscas rápidas mesmo com grandes volumes de dados
- A arquitetura modular permite escalar componentes individualmente

### Segurança

- Os dados são filtrados por matrícula, garantindo que cada usuário acesse apenas suas próprias informações
- Sessões são gerenciadas com timeouts para evitar acesso não autorizado
- Nenhuma informação sensível é armazenada em logs ou caches

### Manutenção

- O sistema de cache de embeddings reduz custos da API da OpenAI
- Os índices FAISS são salvos periodicamente para permitir reconstrução rápida
- Logs detalhados facilitam a depuração e monitoramento

## Limitações e Considerações Futuras

- Atualmente, o sistema não suporta autenticação robusta, dependendo apenas da matrícula
- A extração de dados pode falhar para formatos muito diferentes de contas de luz
- Considerar a implementação de modelos locais para reduzir dependência de APIs externas
- Adicionar suporte para diferentes distribuidoras de energia com layouts diversos
