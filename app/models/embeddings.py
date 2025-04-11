from pydantic import BaseModel, Field
from typing import Dict, List, Any, Optional, Union
import numpy as np
import json
from datetime import datetime

class DocumentoBase(BaseModel):
    """Modelo base para documento para embeddings."""
    id: str = Field(..., description="ID único do documento")
    texto: str = Field(..., description="Texto do documento para embeddings")
    tipo: str = Field(..., description="Tipo do documento")
    
    class Config:
        arbitrary_types_allowed = True

class ClienteDocumento(DocumentoBase):
    """Modelo para documento de cliente."""
    tipo: str = "cliente_info"
    cliente_id: str = Field(..., description="ID do cliente")
    nome: str = Field(..., description="Nome do cliente")
    matricula: str = Field(..., description="Matrícula do cliente")
    endereco: Dict[str, Any] = Field(..., description="Dados de endereço")

class FaturaDocumento(DocumentoBase):
    """Modelo para documento de fatura."""
    tipo: str = "fatura"
    fatura_id: str = Field(..., description="ID da fatura")
    cliente_id: str = Field(..., description="ID do cliente")
    mes_referencia: str = Field(..., description="Mês de referência da fatura")
    consumo: Dict[str, Any] = Field(..., description="Dados de consumo")
    valores: Dict[str, Any] = Field(..., description="Valores da fatura")

class AnaliseDocumento(DocumentoBase):
    """Modelo para documento de análise."""
    tipo: str = "analise"
    cliente_id: str = Field(..., description="ID do cliente")
    periodo: Dict[str, str] = Field(..., description="Período abrangido pela análise")
    num_faturas: int = Field(..., description="Número de faturas analisadas")

class DocumentoEmbedding(BaseModel):
    """Modelo para documento com embedding."""
    documento: Union[ClienteDocumento, FaturaDocumento, AnaliseDocumento]
    embedding: Optional[List[float]] = Field(None, description="Vetor de embedding")
    timestamp: datetime = Field(default_factory=datetime.now, description="Data/hora de criação")
    
    class Config:
        arbitrary_types_allowed = True
    
    def to_dict(self) -> Dict[str, Any]:
        """Converte o modelo para dicionário."""
        documento_dict = self.documento.dict()
        
        # Se tiver embedding, converter para lista
        embedding_list = None
        if self.embedding is not None:
            if isinstance(self.embedding, np.ndarray):
                embedding_list = self.embedding.tolist()
            else:
                embedding_list = self.embedding
        
        return {
            "documento": documento_dict,
            "embedding": embedding_list,
            "timestamp": self.timestamp.isoformat()
        }
    
    def to_json(self) -> str:
        """Converte o modelo para JSON."""
        return json.dumps(self.to_dict())
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'DocumentoEmbedding':
        """Cria uma instância a partir de um dicionário."""
        doc_data = data["documento"]
        
        # Determinar o tipo de documento
        tipo = doc_data.get("tipo", "")
        
        if tipo == "cliente_info":
            documento = ClienteDocumento(**doc_data)
        elif tipo == "fatura":
            documento = FaturaDocumento(**doc_data)
        elif tipo == "analise":
            documento = AnaliseDocumento(**doc_data)
        else:
            documento = DocumentoBase(**doc_data)
        
        # Converter embedding para numpy se necessário
        embedding = data.get("embedding")
        if embedding is not None:
            embedding = np.array(embedding, dtype=np.float32)
        
        # Converter timestamp
        timestamp = datetime.fromisoformat(data["timestamp"]) if "timestamp" in data else datetime.now()
        
        return cls(
            documento=documento, 
            embedding=embedding,
            timestamp=timestamp
        )
    
    @classmethod
    def from_json(cls, json_str: str) -> 'DocumentoEmbedding':
        """Cria uma instância a partir de uma string JSON."""
        data = json.loads(json_str)
        return cls.from_dict(data)


class EmbeddingCache(BaseModel):
    """Modelo para cache de embeddings."""
    chave: str = Field(..., description="Chave única para o embedding (geralmente hash do texto)")
    embedding: List[float] = Field(..., description="Vetor de embedding")
    texto_hash: str = Field(..., description="Hash do texto original")
    modelo: str = Field(..., description="Nome do modelo usado")
    timestamp: datetime = Field(default_factory=datetime.now, description="Data/hora de criação")
    
    class Config:
        arbitrary_types_allowed = True
    
    def to_dict(self) -> Dict[str, Any]:
        """Converte o modelo para dicionário."""
        embedding_list = self.embedding
        if isinstance(self.embedding, np.ndarray):
            embedding_list = self.embedding.tolist()
        
        return {
            "chave": self.chave,
            "embedding": embedding_list,
            "texto_hash": self.texto_hash,
            "modelo": self.modelo,
            "timestamp": self.timestamp.isoformat()
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'EmbeddingCache':
        """Cria uma instância a partir de um dicionário."""
        # Converter embedding para numpy se necessário
        embedding = data["embedding"]
        if not isinstance(embedding, np.ndarray):
            embedding = np.array(embedding, dtype=np.float32)
        
        # Converter timestamp
        timestamp = datetime.fromisoformat(data["timestamp"]) if "timestamp" in data else datetime.now()
        
        return cls(
            chave=data["chave"],
            embedding=embedding,
            texto_hash=data["texto_hash"],
            modelo=data["modelo"],
            timestamp=timestamp
        )


class IndiceMetadata(BaseModel):
    """Modelo para metadados de índice FAISS."""
    id: str = Field(..., description="ID único do índice")
    nome: str = Field(..., description="Nome descritivo do índice")
    dimensao: int = Field(..., description="Dimensão dos vetores")
    modelo_embeddings: str = Field(..., description="Modelo usado para embeddings")
    num_vetores: int = Field(0, description="Número de vetores no índice")
    data_criacao: datetime = Field(default_factory=datetime.now, description="Data de criação")
    ultima_atualizacao: datetime = Field(default_factory=datetime.now, description="Última atualização")
    
    # Mapeamento de IDs para documentos
    # Armazenado separadamente devido ao tamanho potencial
    tem_mapeamento_ids: bool = Field(False, description="Indica se há mapeamento de IDs")