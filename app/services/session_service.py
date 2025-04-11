import logging
import uuid
from typing import Dict, Optional, Any
from datetime import datetime, timedelta

from ..models.schemas import Usuario, Sessao
from ..models.database import session_store

# Configuração de logging
logger = logging.getLogger("services.session")

class SessionManager:
    """
    Gerenciador de sessões de usuários.
    Responsável por criar, atualizar, recuperar e expirar sessões.
    """
    
    def __init__(self):
        """Inicializa o gerenciador de sessões."""
        self.sessoes: Dict[str, Sessao] = {}
        logger.info("Gerenciador de sessões inicializado")
    
    def criar_sessao(self, matricula: str) -> Sessao:
        """
        Cria uma nova sessão para o usuário.
        
        Args:
            matricula: Matrícula do usuário
            
        Returns:
            Sessao: Nova sessão criada
        """
        # Criar ID único para a sessão
        sessao_id = str(uuid.uuid4())
        
        # Criar objetos de usuário e sessão
        usuario = Usuario(matricula=matricula)
        sessao = Sessao(id=sessao_id, usuario=usuario)
        
        # Armazenar a sessão
        self.sessoes[sessao_id] = sessao
        
        # Persistir dados básicos da sessão (opcional)
        session_store.criar_sessao({
            "id": sessao_id,
            "matricula": matricula,
            "criado_em": datetime.now().isoformat()
        })
        
        logger.info(f"Sessão criada: {sessao_id} para matrícula {matricula}")
        return sessao
    
    def obter_sessao(self, sessao_id: str) -> Optional[Sessao]:
        """
        Obtém uma sessão pelo ID.
        
        Args:
            sessao_id: ID da sessão
            
        Returns:
            Sessao ou None: Sessão encontrada ou None se não existir
        """
        # Buscar na memória
        sessao = self.sessoes.get(sessao_id)
        
        if sessao:
            logger.debug(f"Sessão encontrada em memória: {sessao_id}")
            return sessao
        
        # Se não encontrou em memória, tentar restaurar do armazenamento
        sessao_dados = session_store.obter_sessao(sessao_id)
        if sessao_dados:
            # Recriar sessão a partir dos dados persistidos
            try:
                matricula = sessao_dados.get("matricula", "")
                nome = sessao_dados.get("nome", "")
                
                usuario = Usuario(matricula=matricula, nome=nome)
                usuario.validado = sessao_dados.get("validado", False)
                
                sessao = Sessao(id=sessao_id, usuario=usuario)
                
                # Restaurar contexto se existir
                if "contexto" in sessao_dados:
                    sessao.contexto.update(sessao_dados["contexto"])
                
                # Armazenar em memória
                self.sessoes[sessao_id] = sessao
                
                logger.info(f"Sessão restaurada do armazenamento: {sessao_id}")
                return sessao
                
            except Exception as e:
                logger.error(f"Erro ao restaurar sessão {sessao_id}: {str(e)}")
        
        logger.debug(f"Sessão não encontrada: {sessao_id}")
        return None
    
    def atualizar_timestamp_sessao(self, sessao_id: str) -> bool:
        """
        Atualiza o timestamp de última atividade de uma sessão.
        
        Args:
            sessao_id: ID da sessão
            
        Returns:
            bool: True se atualizado com sucesso
        """
        sessao = self.obter_sessao(sessao_id)
        if not sessao:
            return False
        
        # Atualizar timestamp
        sessao.ultima_atividade = datetime.now()
        
        # Persistir alteração
        dados_persistencia = session_store.obter_sessao(sessao_id) or {}
        dados_persistencia["ultima_atividade"] = sessao.ultima_atividade.isoformat()
        session_store.atualizar_sessao(sessao_id, dados_persistencia)
        
        return True
    
    def persistir_sessao(self, sessao: Sessao) -> bool:
        """
        Persiste o estado atual de uma sessão.
        
        Args:
            sessao: Sessão a ser persistida
            
        Returns:
            bool: True se persistida com sucesso
        """
        try:
            # Preparar dados para persistência
            dados_persistencia = {
                "id": sessao.id,
                "matricula": sessao.usuario.matricula,
                "nome": sessao.usuario.nome,
                "validado": sessao.usuario.validado,
                "ultima_atividade": sessao.ultima_atividade.isoformat(),
                "contexto": {
                    # Filtrar apenas dados serializáveis
                    k: v for k, v in sessao.contexto.items()
                    if isinstance(v, (str, int, float, bool, list, dict)) or v is None
                }
            }
            
            # Persistir no armazenamento
            return session_store.atualizar_sessao(sessao.id, dados_persistencia)
            
        except Exception as e:
            logger.error(f"Erro ao persistir sessão {sessao.id}: {str(e)}")
            return False
    
    def remover_sessao(self, sessao_id: str) -> bool:
        """
        Remove uma sessão.
        
        Args:
            sessao_id: ID da sessão
            
        Returns:
            bool: True se removida com sucesso
        """
        # Remover da memória
        if sessao_id in self.sessoes:
            del self.sessoes[sessao_id]
        
        # Remover do armazenamento
        return session_store.remover_sessao(sessao_id)
    
    def limpar_sessoes_inativas(self, tempo_limite_minutos: int = 30) -> int:
        """
        Remove sessões inativas por mais que o tempo limite.
        
        Args:
            tempo_limite_minutos: Tempo limite em minutos
            
        Returns:
            int: Número de sessões removidas
        """
        agora = datetime.now()
        sessoes_removidas = 0
        sessoes_para_remover = []
        
        # Identificar sessões inativas
        for sessao_id, sessao in self.sessoes.items():
            diferenca = (agora - sessao.ultima_atividade).total_seconds() / 60
            
            if diferenca > tempo_limite_minutos:
                sessoes_para_remover.append(sessao_id)
        
        # Remover sessões inativas
        for sessao_id in sessoes_para_remover:
            if self.remover_sessao(sessao_id):
                sessoes_removidas += 1
        
        # Também limpar sessões no armazenamento
        sessoes_removidas += session_store.limpar_sessoes_antigas(tempo_limite_minutos)
        
        if sessoes_removidas > 0:
            logger.info(f"{sessoes_removidas} sessões inativas removidas")
        
        return sessoes_removidas


# Instância global do gerenciador de sessões
session_manager = SessionManager()

# Função para obter a instância do gerenciador
def get_session