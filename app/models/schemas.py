from pydantic import BaseModel, Field, validator
from typing import Dict, List, Optional, Any
from datetime import datetime
import uuid

# Modelos para requisições da API

class UsuarioRequest(BaseModel):
    """Modelo para requisição de início de sessão com matrícula."""
    matricula: str = Field(..., description="Matrícula do usuário na distribuidora")
    
    @validator('matricula')
    def matricula_valida(cls, v):
        """Valida o formato da matrícula."""
        v = v.strip()
        if not v:
            raise ValueError('Matrícula não pode estar vazia')
        
        # Adicione validações específicas para o formato da matrícula, se necessário
        # Exemplo: if not re.match(r'^\d{8,12}$', v):
        #             raise ValueError('Matrícula deve conter entre 8 e 12 dígitos')
        
        return v

class MensagemRequest(BaseModel):
    """Modelo para envio de mensagem."""
    sessao_id: str = Field(..., description="ID da sessão ativa")
    mensagem: str = Field(..., description="Texto da mensagem do usuário")
    
    @validator('mensagem')
    def mensagem_valida(cls, v):
        """Valida o conteúdo da mensagem."""
        v = v.strip()
        if not v:
            raise ValueError('Mensagem não pode estar vazia')
            
        if len(v) > 1000:
            raise ValueError('Mensagem não pode ter mais de 1000 caracteres')
        
        return v

# Modelos para respostas da API

class SessaoResponse(BaseModel):
    """Modelo para resposta de criação de sessão."""
    sessao_id: str = Field(..., description="ID único da sessão")
    nome_usuario: str = Field("", description="Nome do usuário (preenchido após validação)")

class VisualizacaoConsumo(BaseModel):
    """Modelo para dados de visualização de consumo."""
    labels: List[str] = Field(..., description="Rótulos dos períodos (ex: meses)")
    consumo: List[float] = Field(..., description="Valores de consumo em kWh para cada período")
    valores: List[float] = Field(..., description="Valores monetários para cada período")

class PrevisaoItem(BaseModel):
    """Modelo para um item de previsão."""
    mes: str = Field(..., description="Descrição do mês")
    consumo_estimado: float = Field(..., description="Consumo estimado em kWh")
    margem_erro: float = Field(..., description="Margem de erro da estimativa")

class PrevisaoResponse(BaseModel):
    """Modelo para dados de previsão de consumo."""
    previsao_proximos_meses: List[PrevisaoItem] = Field(..., description="Lista de previsões mensais")

class ComparacaoResponse(BaseModel):
    """Modelo para dados de comparação entre períodos."""
    periodo1: str = Field(..., description="Descrição do primeiro período")
    periodo2: str = Field(..., description="Descrição do segundo período")
    consumo1: float = Field(..., description="Consumo no primeiro período (kWh)")
    consumo2: float = Field(..., description="Consumo no segundo período (kWh)")
    diferenca_percentual: float = Field(..., description="Diferença percentual entre os períodos")

class DadosAdicionais(BaseModel):
    """Modelo para dados adicionais na resposta."""
    tipo: str = Field(..., description="Tipo de dados adicionais")
    dados: Optional[Dict[str, Any]] = Field(None, description="Dados estruturados específicos do tipo")
    
    # Metadados opcionais
    nome_cliente: Optional[str] = None
    quantidade_faturas: Optional[int] = None
    periodo_disponivel: Optional[str] = None
    
    # Campos específicos para visualizações
    visualizacao: Optional[VisualizacaoConsumo] = None
    previsao: Optional[PrevisaoResponse] = None
    comparacao: Optional[ComparacaoResponse] = None

class MensagemResponse(BaseModel):
    """Modelo para resposta a uma mensagem do usuário."""
    resposta: str = Field(..., description="Texto da resposta gerada pelo sistema")
    dados_adicionais: Optional[DadosAdicionais] = Field(None, description="Dados adicionais para visualizações ou análises")

# Modelos internos (não expostos diretamente na API)

class Usuario:
    """
    Modelo interno para representação de um usuário.
    
    Atributos:
        matricula: Matrícula do usuário na distribuidora
        nome: Nome do usuário
        validado: Indica se a matrícula foi validada
    """
    def __init__(self, matricula: str, nome: str = ""):
        self.matricula = matricula
        self.nome = nome
        self.validado = False

class Sessao:
    """
    Modelo interno para representação de uma sessão.
    
    Atributos:
        id: ID único da sessão
        usuario: Objeto do usuário associado
        chat_session: Sessão de chat do RagFlow
        ultima_atividade: Timestamp da última atividade
        contexto: Dicionário com informações de contexto da sessão
    """
    def __init__(self, id: str, usuario: Usuario):
        self.id = id
        self.usuario = usuario
        self.chat_session = None
        self.ultima_atividade = datetime.now()
        self.contexto = {
            "matricula": usuario.matricula,
            "dados_carregados": False,
            "ultima_consulta": "",
            "ultima_resposta": ""
        }

# Modelos para estrutura de dados das contas de luz

class Endereco(BaseModel):
    """Modelo para endereço."""
    logradouro: str
    numero: str
    complemento: Optional[str] = ""
    bairro: str
    cidade: str
    estado: str
    cep: str

class Leitura(BaseModel):
    """Modelo para leitura do medidor."""
    data: str
    valor: float

class ConsumoHistorico(BaseModel):
    """Modelo para histórico de consumo."""
    mes: str
    valor: float

class Consumo(BaseModel):
    """Modelo para dados de consumo."""
    total: float
    mediaKWhDia: float
    historico: List[ConsumoHistorico]

class BandeiraTarifaria(BaseModel):
    """Modelo para bandeira tarifária."""
    tipo: str
    valor: float

class ValorAdicional(BaseModel):
    """Modelo para valores adicionais na fatura."""
    descricao: str
    valor: float

class Tributos(BaseModel):
    """Modelo para tributos."""
    icms: float
    pis: float
    cofins: float

class Valores(BaseModel):
    """Modelo para valores da fatura."""
    total: float
    energiaEletrica: float
    transmissao: float
    distribuicao: float
    encargos: float
    tributos: Tributos
    bandeiraTarifaria: BandeiraTarifaria
    outrosValores: List[ValorAdicional]

class Fatura(BaseModel):
    """Modelo para fatura de energia."""
    id: str
    mesReferencia: str
    dataEmissao: str
    dataVencimento: str
    numeroFatura: str
    leituraAnterior: Leitura
    leituraAtual: Leitura
    consumo: Consumo
    valores: Valores

class Meta(BaseModel):
    """Modelo para metadados da conta."""
    distribuidora: str
    tipoTarifa: str
    grupoTarifario: str
    modalidade: str
    tensaoNominal: str
    ultimaAtualizacao: str

class Cliente(BaseModel):
    """Modelo para dados do cliente."""
    id: str
    nome: str
    endereco: Endereco
    numeroCliente: str
    numeroInstalacao: str

class ContaLuz(BaseModel):
    """Modelo completo para dados de conta de luz."""
    cliente: Cliente
    faturas: List[Fatura]
    meta: Meta