from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from typing import Dict, List, Any
from datetime import datetime
import logging

from ..models.schemas import (
    UsuarioRequest, 
    MensagemRequest, 
    MensagemResponse, 
    SessaoResponse
)
from ..services.chat_service import ChatService, get_chat_service
from ..services.embeddings_service import get_embeddings_service
from ..api.dependencies import (
    get_current_user, 
    get_session_manager, 
    validate_session
)

# Configuração de logging
logger = logging.getLogger("api")

# Criação do router
router = APIRouter(tags=["consulta"])

@router.post("/iniciar_sessao", response_model=SessaoResponse)
async def iniciar_sessao(
    usuario_req: UsuarioRequest,
    background_tasks: BackgroundTasks,
    session_manager = Depends(get_session_manager)
):
    """
    Inicia uma nova sessão para o usuário com base na matrícula.
    
    Args:
        usuario_req: Objeto com a matrícula do usuário
        background_tasks: Tarefas em background do FastAPI
        session_manager: Gerenciador de sessões (injetado via dependency)
        
    Returns:
        SessaoResponse com ID da sessão e informações do usuário
    """
    logger.info(f"Solicitação de nova sessão para matrícula: {usuario_req.matricula}")
    
    # Limpar sessões inativas em background
    background_tasks.add_task(session_manager.limpar_sessoes_inativas)
    
    # Criar nova sessão
    try:
        sessao = session_manager.criar_sessao(matricula=usuario_req.matricula)
        
        logger.info(f"Sessão criada: {sessao.id}")
        return SessaoResponse(
            sessao_id=sessao.id,
            nome_usuario=sessao.usuario.nome
        )
    except Exception as e:
        logger.error(f"Erro ao criar sessão: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao criar sessão: {str(e)}"
        )

@router.post("/enviar_mensagem", response_model=MensagemResponse)
async def enviar_mensagem(
    mensagem_req: MensagemRequest,
    background_tasks: BackgroundTasks,
    sessao = Depends(validate_session),
    chat_service: ChatService = Depends(get_chat_service),
    embeddings_service = Depends(get_embeddings_service)
):
    """
    Processa uma mensagem do usuário e retorna uma resposta.
    
    Args:
        mensagem_req: Objeto com ID da sessão e mensagem do usuário
        background_tasks: Tarefas em background do FastAPI
        sessao: Objeto da sessão validada (injetado via dependency)
        chat_service: Serviço de chat (injetado via dependency)
        embeddings_service: Serviço de embeddings (injetado via dependency)
        
    Returns:
        MensagemResponse com resposta do sistema
    """
    logger.info(f"Mensagem recebida na sessão {mensagem_req.sessao_id}: {mensagem_req.mensagem[:50]}...")
    
    # Limpar sessões inativas em background
    session_manager = get_session_manager()
    background_tasks.add_task(session_manager.limpar_sessoes_inativas)
    
    try:
        # Verificar se é a primeira interação (após validação da matrícula)
        if not sessao.usuario.validado:
            # Carregar dados do usuário e validar matrícula
            usuario_validado = await get_current_user(sessao.usuario.matricula, embeddings_service)
            
            if not usuario_validado:
                logger.warning(f"Matrícula inválida: {sessao.usuario.matricula}")
                return MensagemResponse(
                    resposta=f"Desculpe, não encontrei dados para a matrícula {sessao.usuario.matricula}. Por favor, verifique se a matrícula está correta."
                )
            
            # Atualizar dados da sessão
            sessao.usuario.nome = usuario_validado["nome"]
            sessao.usuario.validado = True
            sessao.contexto["dados_carregados"] = True
            
            # Inicializar o chat
            chat_service.inicializar_chat_para_usuario(sessao)
            
            # Resposta de boas-vindas
            resposta_boas_vindas = await chat_service.processar_mensagem(
                sessao=sessao,
                mensagem="Iniciar conversa",  # Mensagem interna para inicialização
                é_primeira_interação=True
            )
            
            return resposta_boas_vindas
        
        # Para mensagens subsequentes
        resposta = await chat_service.processar_mensagem(
            sessao=sessao,
            mensagem=mensagem_req.mensagem
        )
        
        return resposta
        
    except Exception as e:
        logger.error(f"Erro ao processar mensagem: {str(e)}")
        return MensagemResponse(
            resposta="Desculpe, ocorreu um erro ao processar sua mensagem. Por favor, tente novamente."
        )

@router.get("/health")
async def health_check():
    """Verifica se a API está funcionando."""
    return {"status": "OK", "timestamp": datetime.now().isoformat()}