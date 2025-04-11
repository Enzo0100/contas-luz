from typing import Dict, List, Any, Optional
import os
import json
import logging
from datetime import datetime
import uuid

# Configuração de logging
logger = logging.getLogger("models.database")

class JsonDatabase:
    """
    Classe simples para gerenciar dados armazenados em arquivos JSON.
    Útil para armazenar dados estruturados sem necessidade de um banco de dados completo.
    """
    
    def __init__(self, diretorio_base: str):
        """
        Inicializa o banco de dados JSON.
        
        Args:
            diretorio_base: Diretório base para armazenamento dos arquivos
        """
        self.diretorio_base = diretorio_base
        self._garantir_diretorios()
    
    def _garantir_diretorios(self):
        """Garante que os diretórios necessários existam."""
        # Garantir diretório principal
        if not os.path.exists(self.diretorio_base):
            os.makedirs(self.diretorio_base)
            logger.info(f"Diretório base criado: {self.diretorio_base}")
        
        # Garantir subdiretórios para diferentes tipos de dados
        for subdir in ["clientes", "faturas", "sessoes", "cache"]:
            path = os.path.join(self.diretorio_base, subdir)
            if not os.path.exists(path):
                os.makedirs(path)
                logger.info(f"Subdiretório criado: {path}")
    
    def salvar_documento(self, tipo: str, id: str, dados: Dict[str, Any]) -> bool:
        """
        Salva um documento no formato JSON.
        
        Args:
            tipo: Tipo do documento (define o subdiretório)
            id: Identificador único do documento
            dados: Conteúdo do documento a ser salvo
            
        Returns:
            bool: True se salvo com sucesso, False caso contrário
        """
        try:
            # Garantir que a pasta exista
            diretorio = os.path.join(self.diretorio_base, tipo)
            if not os.path.exists(diretorio):
                os.makedirs(diretorio)
            
            # Caminho completo do arquivo
            caminho_arquivo = os.path.join(diretorio, f"{id}.json")
            
            # Adicionar metadados
            dados_com_meta = {
                "id": id,
                "tipo": tipo,
                "ultima_atualizacao": datetime.now().isoformat(),
                "dados": dados
            }
            
            # Salvar o arquivo
            with open(caminho_arquivo, 'w', encoding='utf-8') as f:
                json.dump(dados_com_meta, f, ensure_ascii=False, indent=2)
            
            logger.debug(f"Documento salvo: {tipo}/{id}")
            return True
            
        except Exception as e:
            logger.error(f"Erro ao salvar documento {tipo}/{id}: {str(e)}")
            return False
    
    def carregar_documento(self, tipo: str, id: str) -> Optional[Dict[str, Any]]:
        """
        Carrega um documento a partir do ID.
        
        Args:
            tipo: Tipo do documento
            id: Identificador único do documento
            
        Returns:
            Dict ou None: Conteúdo do documento ou None se não encontrado
        """
        try:
            caminho_arquivo = os.path.join(self.diretorio_base, tipo, f"{id}.json")
            
            if not os.path.exists(caminho_arquivo):
                logger.debug(f"Documento não encontrado: {tipo}/{id}")
                return None
            
            with open(caminho_arquivo, 'r', encoding='utf-8') as f:
                dados = json.load(f)
            
            # Retornar apenas os dados, sem os metadados
            return dados.get("dados")
            
        except Exception as e:
            logger.error(f"Erro ao carregar documento {tipo}/{id}: {str(e)}")
            return None
    
    def listar_documentos(self, tipo: str) -> List[str]:
        """
        Lista todos os IDs de documentos de um determinado tipo.
        
        Args:
            tipo: Tipo dos documentos a listar
            
        Returns:
            List[str]: Lista de IDs dos documentos
        """
        try:
            diretorio = os.path.join(self.diretorio_base, tipo)
            
            if not os.path.exists(diretorio):
                return []
            
            # Listar apenas arquivos JSON
            arquivos = [f for f in os.listdir(diretorio) if f.endswith('.json')]
            
            # Extrair os IDs (removendo a extensão .json)
            ids = [arquivo[:-5] for arquivo in arquivos]
            
            return ids
            
        except Exception as e:
            logger.error(f"Erro ao listar documentos do tipo {tipo}: {str(e)}")
            return []
    
    def remover_documento(self, tipo: str, id: str) -> bool:
        """
        Remove um documento.
        
        Args:
            tipo: Tipo do documento
            id: Identificador único do documento
            
        Returns:
            bool: True se removido com sucesso, False caso contrário
        """
        try:
            caminho_arquivo = os.path.join(self.diretorio_base, tipo, f"{id}.json")
            
            if not os.path.exists(caminho_arquivo):
                logger.debug(f"Documento não encontrado para remoção: {tipo}/{id}")
                return False
            
            # Remover o arquivo
            os.remove(caminho_arquivo)
            logger.debug(f"Documento removido: {tipo}/{id}")
            return True
            
        except Exception as e:
            logger.error(f"Erro ao remover documento {tipo}/{id}: {str(e)}")
            return False
    
    def buscar_documentos(self, tipo: str, filtro: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Busca documentos com base em filtros simples.
        
        Args:
            tipo: Tipo dos documentos a buscar
            filtro: Dicionário com condições de filtro (chave/valor)
            
        Returns:
            List[Dict]: Lista de documentos que atendem aos filtros
        """
        try:
            # Listar IDs
            ids = self.listar_documentos(tipo)
            resultados = []
            
            # Para cada ID, carregar o documento e verificar os filtros
            for id in ids:
                documento = self.carregar_documento(tipo, id)
                
                if not documento:
                    continue
                
                # Verificar se todos os filtros são atendidos
                atende_filtros = True
                for chave, valor in filtro.items():
                    # Suporte a navegação por ponto (ex: "cliente.nome")
                    partes = chave.split('.')
                    valor_doc = documento
                    
                    # Navegar na estrutura do documento
                    for parte in partes:
                        if isinstance(valor_doc, dict) and parte in valor_doc:
                            valor_doc = valor_doc[parte]
                        else:
                            valor_doc = None
                            break
                    
                    # Verificar se o valor coincide
                    if valor_doc != valor:
                        atende_filtros = False
                        break
                
                # Se atende a todos os filtros, adicionar aos resultados
                if atende_filtros:
                    resultados.append(documento)
            
            return resultados
            
        except Exception as e:
            logger.error(f"Erro ao buscar documentos do tipo {tipo}: {str(e)}")
            return []
    
    def gerar_id(self) -> str:
        """
        Gera um ID único.
        
        Returns:
            str: ID único no formato UUID
        """
        return str(uuid.uuid4())


class SessionStore:
    """
    Classe para gerenciamento de sessões.
    Armazena sessões em memória com persistência opcional em JSON.
    """
    
    def __init__(self, db: JsonDatabase = None):
        """
        Inicializa o armazenamento de sessões.
        
        Args:
            db: Instância de JsonDatabase para persistência (opcional)
        """
        self.sessoes = {}  # Armazenamento em memória
        self.db = db  # Para persistência opcional
    
    def criar_sessao(self, dados: Dict[str, Any]) -> str:
        """
        Cria uma nova sessão.
        
        Args:
            dados: Dados da sessão
            
        Returns:
            str: ID da sessão criada
        """
        # Gerar ID único
        sessao_id = str(uuid.uuid4())
        
        # Adicionar timestamp
        dados['criado_em'] = datetime.now().isoformat()
        dados['ultima_atividade'] = datetime.now().isoformat()
        
        # Armazenar em memória
        self.sessoes[sessao_id] = dados
        
        # Persistir se há banco de dados
        if self.db:
            self.db.salvar_documento('sessoes', sessao_id, dados)
        
        return sessao_id
    
    def obter_sessao(self, sessao_id: str) -> Optional[Dict[str, Any]]:
        """
        Obtém uma sessão pelo ID.
        
        Args:
            sessao_id: ID da sessão
            
        Returns:
            Dict ou None: Dados da sessão ou None se não encontrada
        """
        # Buscar na memória
        sessao = self.sessoes.get(sessao_id)
        
        # Se não está na memória, mas há banco de dados, tentar carregar
        if sessao is None and self.db:
            sessao = self.db.carregar_documento('sessoes', sessao_id)
            if sessao:
                # Atualizar cache em memória
                self.sessoes[sessao_id] = sessao
        
        return sessao
    
    def atualizar_sessao(self, sessao_id: str, dados: Dict[str, Any]) -> bool:
        """
        Atualiza dados de uma sessão existente.
        
        Args:
            sessao_id: ID da sessão
            dados: Novos dados da sessão
            
        Returns:
            bool: True se atualizado com sucesso, False caso contrário
        """
        # Verificar se a sessão existe
        if sessao_id not in self.sessoes and not (self.db and self.db.carregar_documento('sessoes', sessao_id)):
            return False
        
        # Atualizar timestamp
        dados['ultima_atividade'] = datetime.now().isoformat()
        
        # Atualizar em memória
        self.sessoes[sessao_id] = dados
        
        # Persistir se há banco de dados
        if self.db:
            self.db.salvar_documento('sessoes', sessao_id, dados)
        
        return True
    
    def remover_sessao(self, sessao_id: str) -> bool:
        """
        Remove uma sessão.
        
        Args:
            sessao_id: ID da sessão
            
        Returns:
            bool: True se removido com sucesso, False caso contrário
        """
        # Remover da memória
        if sessao_id in self.sessoes:
            del self.sessoes[sessao_id]
        
        # Remover da persistência se houver
        if self.db:
            return self.db.remover_documento('sessoes', sessao_id)
        
        return True
    
    def limpar_sessoes_antigas(self, tempo_limite_minutos: int = 30) -> int:
        """
        Remove sessões inativas por mais que o tempo limite.
        
        Args:
            tempo_limite_minutos: Tempo limite em minutos
            
        Returns:
            int: Número de sessões removidas
        """
        agora = datetime.now()
        sessoes_removidas = 0
        
        # Listar IDs para não modificar o dicionário durante iteração
        ids_sessoes = list(self.sessoes.keys())
        
        for sessao_id in ids_sessoes:
            sessao = self.sessoes[sessao_id]
            
            # Converter string para datetime
            ultima_atividade = datetime.fromisoformat(sessao['ultima_atividade'])
            
            # Calcular diferença em minutos
            diferenca = (agora - ultima_atividade).total_seconds() / 60
            
            # Remover se inativa por mais que o tempo limite
            if diferenca > tempo_limite_minutos:
                self.remover_sessao(sessao_id)
                sessoes_removidas += 1
        
        return sessoes_removidas


# Inicializar banco de dados se o módulo for importado
from ..config import settings

db = JsonDatabase(settings.DATA_DIR)
session_store = SessionStore(db)

# Exportar instâncias
__all__ = ["db", "session_store"]