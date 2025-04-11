# Exportar classes e funções principais

from .schemas import (
    UsuarioRequest, 
    MensagemRequest, 
    MensagemResponse, 
    SessaoResponse,
    VisualizacaoConsumo,
    PrevisaoItem,
    PrevisaoResponse,
    ComparacaoResponse,
    DadosAdicionais,
    Usuario,
    Sessao,
    ContaLuz,
    Cliente,
    Fatura,
    Meta
)

from .database import (
    db,
    session_store,
    JsonDatabase,
    SessionStore
)

from .embeddings import (
    DocumentoBase,
    ClienteDocumento,
    FaturaDocumento,
    AnaliseDocumento,
    DocumentoEmbedding,
    EmbeddingCache,
    IndiceMetadata
)

# Lista de exportação
__all__ = [
    # Schemas de API
    "UsuarioRequest", 
    "MensagemRequest", 
    "MensagemResponse", 
    "SessaoResponse",
    "VisualizacaoConsumo",
    "PrevisaoItem",
    "PrevisaoResponse",
    "ComparacaoResponse",
    "DadosAdicionais",
    
    # Modelos internos
    "Usuario",
    "Sessao",
    
    # Modelos de dados
    "ContaLuz",
    "Cliente",
    "Fatura",
    "Meta",
    
    # Banco de dados
    "db",
    "session_store",
    "JsonDatabase",
    "SessionStore",
    
    # Embeddings
    "DocumentoBase",
    "ClienteDocumento",
    "FaturaDocumento",
    "AnaliseDocumento",
    "DocumentoEmbedding",
    "EmbeddingCache",
    "IndiceMetadata"
]