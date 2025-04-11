# Sistema de Consulta de Contas de Luz com RAGFlow e FAISS

Este projeto implementa um sistema de consulta inteligente para contas de luz, utilizando processamento de linguagem natural, OCR para extração de dados de PDFs, embeddings da OpenAI e busca vetorial com FAISS para fornecer respostas precisas sobre consumo e gastos de energia elétrica.

## Recursos Principais

- ✅ Extração de dados de PDFs de contas de luz usando e DeepDocs OCR
- ✅ Processamento e estruturação padronizada dos dados extraídos
- ✅ Geração de embeddings vetoriais usando modelos da OpenAI
- ✅ Indexação e busca eficiente com FAISS
- ✅ API REST para integração com aplicações
- ✅ Interface de chat para consultas em linguagem natural
- ✅ Visualizações de dados de consumo e gastos
- ✅ Previsão de consumo futuro baseada em dados históricos

## Arquitetura

O sistema é baseado em uma arquitetura de Retrieval Augmented Generation (RAG) e consiste em quatro componentes principais:

1. **Extração de Dados**: Utiliza RagFlow com DeepDocs para extrair dados estruturados dos PDFs
2. **Indexação Vetorial**: Gera embeddings com OpenAI e cria índices FAISS para busca eficiente
3. **API de Consulta**: Processa consultas e gera respostas contextualizadas via FastAPI
4. **Interface Web**: Permite interação com o sistema através de chat e visualizações

Para mais detalhes sobre a arquitetura, consulte a [documentação de arquitetura](./docs/architecture.md).

## Requisitos

- Python 3.8+
- RagFlow 1.0+ (com DeepDocs)
- FastAPI 0.68+
- OpenAI API (para embeddings e LLM)
- FAISS 1.7+
- Outras dependências listadas em `requirements.txt`

## Instalação

1. Clone o repositório:
   ```
   git clone https://github.com/seu-usuario/sistema-consulta-energia.git
   cd sistema-consulta-energia
   ```

2. Crie e ative um ambiente virtual:
   ```
   python -m venv venv
   source venv/bin/activate  # No Windows: venv\Scripts\activate
   ```

3. Instale as dependências:
   ```
   pip install -r requirements.txt
   ```

4. Configure as variáveis de ambiente (crie um arquivo `.env` baseado em `.env.example`):
   ```
   OPENAI_API_KEY=sua-chave-api
   DIRETORIO_DADOS=./data/processed
   DIRETORIO_FAISS=./data/faiss_index
   ```

## Uso

### 1. Extração de Dados

Para processar PDFs de contas de luz e extrair dados estruturados:

```
python scripts/extract_data.py --input ./data/raw --output ./data/processed
```

### 2. Geração de Embeddings e Índice FAISS

Para gerar embeddings e construir o índice FAISS:

```
python scripts/generate_embeddings.py --data ./data/processed
```

### 3. Executando a API

Para iniciar o servidor API:

```
uvicorn app.main:app --reload --port 8000
```

A API estará disponível em `http://localhost:8000`.

### 4. Interface Web

Para usar a interface web, abra o arquivo `frontend/index.html` em seu navegador ou sirva-o com um servidor web simples:

```
cd frontend
python -m http.server 8080
```

A interface estará disponível em `http://localhost:8080`.

## API

O sistema expõe uma API REST com os seguintes endpoints principais:

- `POST /iniciar_sessao`: Inicia uma sessão com base na matrícula do cliente
- `POST /enviar_mensagem`: Processa uma consulta e retorna resposta com dados contextualizados
- `GET /health`: Verifica a saúde do serviço

Para mais detalhes, consulte a [documentação da API](./docs/api_reference.md).

## Exemplos de Consultas

O sistema suporta uma ampla variedade de consultas em linguagem natural, incluindo:

- "Qual foi meu consumo em março de 2023?"
- "Quanto gastei de energia no último trimestre?"
- "Como meu consumo atual se compara ao mesmo período do ano passado?"
- "Qual mês tive o maior gasto com energia?"
- "Pode fazer uma previsão do meu consumo para os próximos meses?"

## Contribuindo

Contribuições são bem-vindas! Por favor, siga estas etapas:

1. Faça um fork do projeto
2. Crie uma branch para sua feature (`git checkout -b feature/nova-feature`)
3. Faça commit das suas mudanças (`git commit -am 'Adiciona nova feature'`)
4. Push para a branch (`git push origin feature/nova-feature`)
5. Crie um novo Pull Request

## Licença

Este projeto está licenciado sob a licença MIT - veja o arquivo [LICENSE](LICENSE) para detalhes.

## Documentação Adicional

- [Guia do Usuário](./docs/user_guide.md)
- [Arquitetura](./docs/architecture.md)
- [Referência da API](./docs/api_reference.md)