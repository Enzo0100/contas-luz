from fastapi import Depends, HTTPException, status
from typing import Dict, Any, Optional
import logging

from ..models.schemas import MensagemRequest
from ..services.session_service import SessionManager, Sessao
from ..services.embeddings_service import EmbeddingsService

# Configuração de logging
logger = logging.getLogger("api.dependencies")

# Instância global do gerenciador de sessões
_session_manager = SessionManager()

def get_session_manager() -> SessionManager:
    """
    Obtém a instância global do gerenciador de sessões.
    
    Returns:
        SessionManager: Instância do gerenciador de sessões
    """
    return _session_manager

async def get_current_user(matricula: str, embeddings_service: EmbeddingsService) -> Optional[Dict[str, Any]]:
    """
    Obtém os dados do usuário a partir da matrícula.
    
    Args:
        matricula: Matrícula do usuário
        embeddings_service: Serviço de embeddings
        
    Returns:
        Dados do usuário ou None se não encontrado
    """
    try:
        # Buscar informações básicas do cliente
        cliente_info = embeddings_service.buscar_cliente_por_matricula(matricula)
        
        if not cliente_info:
            logger.warning(f"Usuário não encontrado para matrícula: {matricula}")
            return None
            
        return {
            "matricula": matricula,
            "nome": cliente_info.get("nome", "Cliente"),
            "numero_instalacao": cliente_info.get("numeroInstalacao", ""),
            "endereco": cliente_info.get("endereco", {})
        }
    except Exception as e:
        logger.error(f"Erro ao obter dados do usuário {matricula}: {str(e)}")
        return None

async def validate_session(mensagem_req: MensagemRequest) -> Sessao:
    """
    Valida e retorna a sessão com base no ID de sessão fornecido.
    
    Args:
        mensagem_req: Requisição com ID da sessão
        
    Returns:
        Sessao: Objeto da sessão validada
        
    Raises:
        HTTPException: Se a sessão não for encontrada ou estiver inválida
    """
    session_manager = get_session_manager()
    sessao_id = mensagem_req.sessao_id
    
    if not sessao_id:
        logger.error("ID de sessão não fornecido")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="ID de sessão é obrigatório"
        )
    
    sessao = session_manager.obter_sessao(sessao_id)
    
    if not sessao:
        logger.error(f"Sessão não encontrada: {sessao_id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Sessão não encontrada. Por favor, inicie uma nova sessão."
        )
    
    # Atualizar timestamp de última atividade
    session_manager.atualizar_timestamp_sessao(sessao_id)
    
    return sessao

def get_embeddings_service():
    """
    Obtém a instância do serviço de embeddings.
    Esta dependency injection permite isolar dependências e facilitar testes.
    
    Returns:
        EmbeddingsService: Instância do serviço de embeddings
    """
    from ..services.embeddings_service import embeddings_service
    return embeddings_service

def get_chat_service():
    """
    Obtém a instância do serviço de chat.
    Esta dependency injection permite isolar dependências e facilitar testes.
    
    Returns:
        ChatService: Instância do serviço de chat
    """
    from ..services.chat_service import chat_service
    return chat_service