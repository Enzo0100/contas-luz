import logging
import json
import re
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
import numpy as np

from ragflow import RagFlow
from ragflow.chat import ChatSession
from ragflow.llm import LLMConfig
from openai import OpenAI

from ..models.schemas import (
    MensagemResponse, 
    DadosAdicionais, 
    Sessao,
    VisualizacaoConsumo,
    PrevisaoItem,
    PrevisaoResponse
)
from ..services.embeddings_service import EmbeddingsService, get_embeddings_service
from ..config import settings

# Configuração de logging
logger = logging.getLogger("services.chat")

class ChatService:
    """
    Serviço para gerenciar interações de chat e processamento de consultas.
    Responsável por:
    - Gerenciar sessões de chat do RagFlow
    - Processar consultas em linguagem natural
    - Utilizar embeddings e FAISS para buscar contexto relevante
    - Gerar respostas sobre contas de luz
    """
    
    def __init__(self):
        """Inicializa o serviço de chat."""
        # Configurações
        self.modelo_chat = settings.MODELO_CHAT
        self.temperatura = settings.TEMPERATURA_CHAT
        self.max_tokens = settings.MAX_TOKENS_CHAT
        self.api_key = settings.OPENAI_API_KEY
        
        # Cliente OpenAI
        self.client = OpenAI(api_key=self.api_key)
        
        # RagFlow
        self.ragflow = RagFlow()
        
        # Flag de inicialização
        self.inicializado = False
        
        logger.info(f"Serviço de chat criado com modelo: {self.modelo_chat}")
    
    async def inicializar(self):
        """Inicializa o serviço de chat."""
        if self.inicializado:
            return
        
        logger.info("Inicializando serviço de chat...")
        
        # Configurar RagFlow
        # Se necessário, adicionar processadores específicos aqui
        
        self.inicializado = True
        logger.info("Serviço de chat inicializado")
    
    def inicializar_chat_para_usuario(self, sessao: Sessao):
        """
        Inicializa uma sessão de chat do RagFlow para um usuário.
        
        Args:
            sessao: Sessão do usuário
        """
        # Configurar LLM
        llm_config = LLMConfig(
            model=self.modelo_chat,
            temperature=self.temperatura,
            max_tokens=self.max_tokens,
            api_key=self.api_key
        )
        
        # Criar prompt do sistema
        system_prompt = self._criar_prompt_sistema(sessao)
        
        # Criar sessão de chat
        chat_session = ChatSession(
            llm_config=llm_config,
            system_prompt=system_prompt
        )
        
        # Armazenar na sessão do usuário
        sessao.chat_session = chat_session
        logger.info(f"Chat inicializado para sessão {sessao.id}")
    
    def _criar_prompt_sistema(self, sessao: Sessao) -> str:
        """
        Cria o prompt do sistema para o assistente.
        
        Args:
            sessao: Sessão do usuário
            
        Returns:
            str: Texto do prompt do sistema
        """
        nome_usuario = sessao.usuario.nome or "Cliente"
        matricula = sessao.usuario.matricula
        
        return f"""
        Você é um assistente virtual especializado em consultas de contas de luz. 
        Você tem acesso aos dados de consumo e valores das faturas de {nome_usuario} (matrícula: {matricula}).
        
        Suas principais capacidades são:
        
        1. Consultar o consumo de energia em períodos específicos
        2. Informar valores gastos em determinados períodos
        3. Analisar o histórico de consumo e gastos
        4. Fazer previsões simples de consumo e gastos futuros
        5. Comparar diferentes períodos de consumo
        
        Ao responder, você deve:
        
        - Ser conciso e ir direto ao ponto 
        - Fornecer dados precisos e contextualizados
        - Informar a fonte dos dados (por exemplo, "Segundo sua fatura de Março/2023...")
        - Não usar termos técnicos complexos sem explicação
        - Sugerir maneiras de economizar