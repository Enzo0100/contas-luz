# Referência da API de Consulta de Contas de Luz

## Visão Geral

A API de Consulta de Contas de Luz fornece endpoints para autenticar usuários por matrícula e processar consultas em linguagem natural sobre dados de contas de energia elétrica. A API usa o FastAPI framework e segue os princípios REST.

Base URL: `http://localhost:8000` (ambiente de desenvolvimento)

## Autenticação

A API utiliza autenticação baseada em sessão. O fluxo de autenticação é:

1. Iniciar uma sessão com a matrícula do cliente
2. Usar o ID de sessão retornado para todas as chamadas subsequentes

## Endpoints

### Iniciar Sessão

Inicia uma nova sessão para o usuário com base na matrícula.

```
POST /iniciar_sessao
```

**Request Body:**
```json
{
  "matricula": "123456789"
}
```

**Response:**
```json
{
  "sessao_id": "550e8400-e29b-41d4-a716-446655440000",
  "nome_usuario": ""
}
```

**Códigos de Status:**
- `200 OK`: Sessão iniciada com sucesso
- `400 Bad Request`: Parâmetros inválidos

**Notas:**
- O campo `nome_usuario` será preenchido após a validação da matrícula
- O `sessao_id` deve ser armazenado pelo cliente e enviado em todas as requisições subsequentes

### Enviar Mensagem

Processa uma mensagem do usuário e retorna uma resposta.

```
POST /enviar_mensagem
```

**Request Body:**
```json
{
  "sessao_id": "550e8400-e29b-41d4-a716-446655440000",
  "mensagem": "Qual foi meu consumo no último mês?"
}
```

**Response:**
```json
{
  "resposta": "No último mês (Fevereiro/2023), seu consumo foi de 150 kWh, resultando em um valor de R$ 120,50.",
  "dados_adicionais": {
    "tipo": "visualizacao_consumo",
    "dados": {
      "labels": ["Jan/2023", "Fev/2023", "Mar/2023"],
      "consumo": [145, 150, 160],
      "valores": [115.80, 120.50, 128.00]
    }
  }
}
```

**Códigos de Status:**
- `200 OK`: Mensagem processada com sucesso
- `404 Not Found`: Sessão não encontrada
- `400 Bad Request`: Parâmetros inválidos

**Notas:**
- O campo `dados_adicionais` pode conter informações estruturadas para visualizações ou análises
- Os tipos possíveis para `dados_adicionais.tipo` incluem:
  - `visualizacao_consumo`: Dados históricos de consumo para visualização
  - `previsao`: Previsões de consumo futuro
  - `comparacao`: Comparações entre períodos

### Verificar Saúde da API

Verifica se a API está funcionando corretamente.

```
GET /health
```

**Response:**
```json
{
  "status": "OK",
  "timestamp": "2023-04-10T14:30:15.123456"
}
```

**Códigos de Status:**
- `200 OK`: API funcionando normalmente

## Tipos de Dados

### Objeto Sessão

Representa uma sessão ativa do usuário.

| Campo | Tipo | Descrição |
|-------|------|-----------|
| sessao_id | string | Identificador único da sessão (UUID) |
| nome_usuario | string | Nome do usuário (preenchido após validação) |

### Objeto Mensagem

Representa uma mensagem enviada pelo usuário.

| Campo | Tipo | Descrição |
|-------|------|-----------|
| sessao_id | string | ID da sessão ativa |
| mensagem | string | Texto da mensagem enviada pelo usuário |

### Objeto Resposta

Representa a resposta do sistema a uma mensagem do usuário.

| Campo | Tipo | Descrição |
|-------|------|-----------|
| resposta | string | Texto da resposta gerada pelo sistema |
| dados_adicionais | object | Dados estruturados adicionais (opcional) |

### Objeto VisualizacaoConsumo

Representa dados para visualização de consumo.

| Campo | Tipo | Descrição |
|-------|------|-----------|
| labels | string[] | Rótulos dos períodos (ex: meses) |
| consumo | number[] | Valores de consumo em kWh para cada período |
| valores | number[] | Valores monetários para cada período |

### Objeto Previsao

Representa previsões de consumo futuro.

| Campo | Tipo | Descrição |
|-------|------|-----------|
| previsao_proximos_meses | object[] | Lista de previsões mensais |
| previsao_proximos_meses[].mes | string | Descrição do mês |
| previsao_proximos_meses[].consumo_estimado | number | Consumo estimado em kWh |
| previsao_proximos_meses[].margem_erro | number | Margem de erro da estimativa |

## Gestão de Sessão

- As sessões expiram após 30 minutos de inatividade
- Uma nova mensagem em uma sessão existente renova o tempo de expiração
- Não há limite definido de mensagens por sessão

## Exemplos de Uso

### Iniciar uma nova sessão

```bash
curl -X POST http://localhost:8000/iniciar_sessao \
  -H "Content-Type: application/json" \
  -d '{"matricula": "123456789"}'
```

### Enviar uma mensagem

```bash
curl -X POST http://localhost:8000/enviar_mensagem \
  -H "Content-Type: application/json" \
  -d '{"sessao_id": "550e8400-e29b-41d4-a716-446655440000", "mensagem": "Qual foi meu consumo no último mês?"}'
```

## Códigos de Erro

| Código | Descrição | Causa Provável |
|--------|-----------|----------------|
| 400 | Bad Request | Parâmetros de requisição inválidos |
| 404 | Not Found | Sessão não encontrada ou expirada |
| 500 | Internal Server Error | Erro interno do servidor |

## Limitações e Considerações

- A API tem um limite de 100 requisições por minuto por IP
- O tamanho máximo de uma mensagem é de 1000 caracteres
- As respostas podem demorar alguns segundos devido ao processamento do LLM
- Considere implementar uma lógica de retry em caso de falhas temporárias