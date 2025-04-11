import os
import json
import logging
import numpy as np
import faiss
from typing import Dict, List, Any, Optional, Tuple, Union
from datetime import datetime

from ..models.embeddings import (
    DocumentoBase,
    ClienteDocumento,
    FaturaDocumento,
    AnaliseDocumento,
    DocumentoEmbedding,
    IndiceMetadata
)
from ..config import settings

# Configuração de logging
logger = logging.getLogger("services.faiss")

class FaissService:
    """
    Serviço especializado para gerenciar índices FAISS.
    Esta classe lida exclusivamente com as operações de baixo nível do FAISS,
    enquanto o EmbeddingsService lida com a camada de alto nível e integração.
    """
    
    def __init__(self):
        """Inicializa o serviço FAISS."""
        # Configurações
        self.diretorio_indices = settings.DIRETORIO_FAISS
        
        # Garantir que o diretório exista
        os.makedirs(self.diretorio_indices, exist_ok=True)
        
        # Índices carregados (para suportar múltiplos índices)
        self.indices: Dict[str, faiss.Index] = {}
        self.metadados: Dict[str, IndiceMetadata] = {}
        self.mapeamentos: Dict[str, Dict[int, Any]] = {}
        
        # Flag de inicialização
        self.inicializado = False
        
        logger.info("Serviço FAISS inicializado")
    
    async def inicializar(self):
        """Inicializa o serviço FAISS, carregando índices existentes."""
        if self.inicializado:
            return
        
        logger.info("Carregando índices FAISS existentes...")
        
        # Listar todos os arquivos de índice
        arquivos_indice = [f for f in os.listdir(self.diretorio_indices) if f.endswith('.index')]
        
        if not arquivos_indice:
            logger.info("Nenhum índice encontrado.")
            self.inicializado = True
            return
        
        # Agrupar arquivos por prefixo (ID do índice)
        indices_por_id = {}
        for arquivo in arquivos_indice:
            # Formato esperado: id_timestamp.index
            partes = arquivo.split('_')
            if len(partes) >= 2:
                indice_id = partes[0]
                if indice_id not in indices_por_id:
                    indices_por_id[indice_id] = []
                indices_por_id[indice_id].append(arquivo)
        
        # Carregar cada índice (apenas o mais recente de cada ID)
        for indice_id, arquivos in indices_por_id.items():
            # Ordenar por timestamp (assumindo formato específico)
            arquivos.sort(reverse=True)
            arquivo_mais_recente = arquivos[0]
            
            # Tentar carregar este índice
            await self.carregar_indice(indice_id, arquivo_mais_recente)
        
        self.inicializado = True
        logger.info(f"Serviço FAISS inicializado com {len(self.indices)} índices")
    
    async def carregar_indice(self, indice_id: str, nome_arquivo: str = None) -> bool:
        """
        Carrega um índice FAISS específico.
        
        Args:
            indice_id: ID do índice
            nome_arquivo: Nome do arquivo específico ou None para buscar o mais recente
            
        Returns:
            bool: True se carregado com sucesso
        """
        try:
            # Se não for especificado um nome de arquivo, buscar o mais recente
            if nome_arquivo is None:
                arquivos = [f for f in os.listdir(self.diretorio_indices) 
                          if f.startswith(f"{indice_id}_") and f.endswith('.index')]
                if not arquivos:
                    logger.warning(f"Nenhum arquivo de índice encontrado para ID: {indice_id}")
                    return False
                
                # Ordenar por timestamp (presumindo formato específico)
                arquivos.sort(reverse=True)
                nome_arquivo = arquivos[0]
            
            # Caminho completo para o arquivo do índice
            caminho_indice = os.path.join(self.diretorio_indices, nome_arquivo)
            
            # Extrair timestamp do nome do arquivo
            partes = nome_arquivo.split('_')
            timestamp = partes[1].split('.')[0] if len(partes) > 1 else None
            
            # Buscar arquivo de mapeamento correspondente
            nome_mapeamento = f"{indice_id}_{timestamp}_mapping.json" if timestamp else None
            caminho_mapeamento = os.path.join(self.diretorio_indices, nome_mapeamento) if nome_mapeamento else None
            
            # Buscar arquivo de metadados correspondente
            nome_metadata = f"{indice_id}_{timestamp}_metadata.json" if timestamp else None
            caminho_metadata = os.path.join(self.diretorio_indices, nome_metadata) if nome_metadata else None
            
            # Carregar o índice FAISS
            self.indices[indice_id] = faiss.read_index(caminho_indice)
            
            # Carregar o mapeamento se existir
            self.mapeamentos[indice_id] = {}
            if caminho_mapeamento and os.path.exists(caminho_mapeamento):
                with open(caminho_mapeamento, 'r', encoding='utf-8') as f:
                    mapeamento_raw = json.load(f)
                
                # Converter as chaves para inteiros
                self.mapeamentos[indice_id] = {int(k): v for k, v in mapeamento_raw.items()}
            
            # Carregar metadados se existirem
            if caminho_metadata and os.path.exists(caminho_metadata):
                with open(caminho_metadata, 'r', encoding='utf-8') as f:
                    metadata_raw = json.load(f)
                
                self.metadados[indice_id] = IndiceMetadata(**metadata_raw)
            else:
                # Criar metadados básicos
                self.metadados[indice_id] = IndiceMetadata(
                    id=indice_id,
                    nome=f"Índice {indice_id}",
                    dimensao=self.indices[indice_id].d,
                    modelo_embeddings="desconhecido",
                    num_vetores=self.indices[indice_id].ntotal,
                    data_criacao=datetime.now(),
                    ultima_atualizacao=datetime.now(),
                    tem_mapeamento_ids=(len(self.mapeamentos[indice_id]) > 0)
                )
            
            logger.info(f"Índice {indice_id} carregado: {self.indices[indice_id].ntotal} vetores")
            return True
            
        except Exception as e:
            logger.error(f"Erro ao carregar índice {indice_id}: {str(e)}")
            return False
    
    async def criar_indice(self, 
                          indice_id: str, 
                          dimensao: int, 
                          tipo: str = "flat", 
                          metadados: Dict[str, Any] = None) -> bool:
        """
        Cria um novo índice FAISS.
        
        Args:
            indice_id: ID do índice
            dimensao: Dimensão dos vetores
            tipo: Tipo de índice ('flat', 'ivf', 'hnsw')
            metadados: Metadados adicionais para o índice
            
        Returns:
            bool: True se criado com sucesso
        """
        try:
            # Verificar se já existe um índice com este ID
            if indice_id in self.indices:
                logger.warning(f"Já existe um índice com ID {indice_id}")
                return False
            
            # Criar índice de acordo com o tipo
            if tipo == "flat":
                # Índice exato (mais preciso, mais lento)
                index = faiss.IndexFlatL2(dimensao)
            elif tipo == "ivf":
                # Índice IVF (mais rápido, menos preciso)
                # Requer dados para treinamento, implementação simplificada
                quantizer = faiss.IndexFlatL2(dimensao)
                nlist = 100  # número de células Voronoi
                index = faiss.IndexIVFFlat(quantizer, dimensao, nlist)
                index.nprobe = 10  # número de células a verificar
            elif tipo == "hnsw":
                # Índice HNSW (hierárquico, muito rápido)
                index = faiss.IndexHNSWFlat(dimensao, 32)  # 32 conexões por nó
            else:
                # Padrão para flat se tipo desconhecido
                logger.warning(f"Tipo de índice desconhecido: {tipo}, usando 'flat'")
                index = faiss.IndexFlatL2(dimensao)
            
            # Armazenar o índice
            self.indices[indice_id] = index
            
            # Inicializar mapeamento
            self.mapeamentos[indice_id] = {}
            
            # Criar metadados
            metadados_base = {
                "id": indice_id,
                "nome": metadados.get("nome", f"Índice {indice_id}") if metadados else f"Índice {indice_id}",
                "dimensao": dimensao,
                "tipo_indice": tipo,
                "modelo_embeddings": metadados.get("modelo_embeddings", "não especificado") if metadados else "não especificado",
                "data_criacao": datetime.now(),
                "ultima_atualizacao": datetime.now(),
                "num_vetores": 0,
                "tem_mapeamento_ids": True
            }
            
            # Atualizar com metadados adicionais
            if metadados:
                metadados_base.update({k: v for k, v in metadados.items() if k not in ["id", "dimensao", "data_criacao"]})
            
            self.metadados[indice_id] = IndiceMetadata(**metadados_base)
            
            logger.info(f"Índice {indice_id} do tipo {tipo} criado com dimensão {dimensao}")
            return True
            
        except Exception as e:
            logger.error(f"Erro ao criar índice {indice_id}: {str(e)}")
            return False
    
    async def adicionar_vetores(self, 
                              indice_id: str, 
                              vetores: np.ndarray, 
                              mapeamento: Dict[int, Any] = None) -> bool:
        """
        Adiciona vetores a um índice existente.
        
        Args:
            indice_id: ID do índice
            vetores: Matriz de vetores (numpy array)
            mapeamento: Dicionário mapeando índices para documentos
            
        Returns:
            bool: True se adicionado com sucesso
        """
        if indice_id not in self.indices:
            logger.error(f"Índice {indice_id} não encontrado")
            return False
        
        try:
            # Garantir que os vetores estão no formato correto
            if len(vetores.shape) != 2:
                raise ValueError("Os vetores devem ser uma matriz 2D")
            
            # Verificar a dimensão
            if vetores.shape[1] != self.indices[indice_id].d:
                raise ValueError(f"Dimensão dos vetores ({vetores.shape[1]}) não corresponde ao índice ({self.indices[indice_id].d})")
            
            # Obter o número atual de vetores no índice
            offset = self.indices[indice_id].ntotal
            
            # Adicionar os vetores
            self.indices[indice_id].add(vetores)
            
            # Atualizar o mapeamento se fornecido
            if mapeamento:
                # Ajustar os índices com o offset
                for idx, doc in mapeamento.items():
                    self.mapeamentos[indice_id][offset + idx] = doc
            
            # Atualizar metadados
            self.metadados[indice_id].num_vetores = self.indices[indice_id].ntotal
            self.metadados[indice_id].ultima_atualizacao = datetime.now()
            
            logger.info(f"{vetores.shape[0]} vetores adicionados ao índice {indice_id}")
            return True
            
        except Exception as e:
            logger.error(f"Erro ao adicionar vetores ao índice {indice_id}: {str(e)}")
            return False
    
    async def salvar_indice(self, indice_id: str) -> bool:
        """
        Salva um índice em disco.
        
        Args:
            indice_id: ID do índice
            
        Returns:
            bool: True se salvo com sucesso
        """
        if indice_id not in self.indices:
            logger.error(f"Índice {indice_id} não encontrado")
            return False
        
        try:
            # Gerar timestamp para nomes de arquivo
            timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
            
            # Caminho para o arquivo do índice
            caminho_indice = os.path.join(self.diretorio_indices, f"{indice_id}_{timestamp}.index")
            
            # Salvar índice FAISS
            faiss.write_index(self.indices[indice_id], caminho_indice)
            
            # Salvar mapeamento
            if self.mapeamentos.get(indice_id):
                caminho_mapeamento = os.path.join(self.diretorio_indices, f"{indice_id}_{timestamp}_mapping.json")
                
                # Converter para formato serializável
                mapeamento_serializavel = {}
                for idx, doc in self.mapeamentos[indice_id].items():
                    # Se for um modelo Pydantic
                    if hasattr(doc, "dict"):
                        mapeamento_serializavel[str(idx)] = doc.dict()
                    else:
                        # Caso seja outro tipo de objeto
                        mapeamento_serializavel[str(idx)] = doc
                
                with open(caminho_mapeamento, 'w', encoding='utf-8') as f:
                    json.dump(mapeamento_serializavel, f, ensure_ascii=False, indent=2)
            
            # Salvar metadados
            if self.metadados.get(indice_id):
                caminho_metadata = os.path.join(self.diretorio_indices, f"{indice_id}_{timestamp}_metadata.json")
                
                # Atualizar timestamp
                self.metadados[indice_id].ultima_atualizacao = datetime.now()
                
                with open(caminho_metadata, 'w', encoding='utf-8') as f:
                    json.dump(self.metadados[indice_id].dict(), f, ensure_ascii=False, indent=2)
            
            logger.info(f"Índice {indice_id} salvo em {caminho_indice}")
            return True
            
        except Exception as e:
            logger.error(f"Erro ao salvar índice {indice_id}: {str(e)}")
            return False
    
    async def buscar(self, 
                   indice_id: str, 
                   vetor_consulta: np.ndarray, 
                   k: int = 5) -> Tuple[List[int], List[float]]:
        """
        Realiza uma busca por similaridade no índice FAISS.
        
        Args:
            indice_id: ID do índice
            vetor_consulta: Vetor de consulta
            k: Número de resultados a retornar
            
        Returns:
            Tuple[List[int], List[float]]: Tupla com (índices, scores)
        """
        if indice_id not in self.indices:
            logger.error(f"Índice {indice_id} não encontrado")
            return [], []
        
        try:
            # Garantir que o vetor está no formato correto
            if len(vetor_consulta.shape) == 1:
                # Converter para matriz 2D
                vetor_consulta = np.array([vetor_consulta], dtype=np.float32)
            
            # Verificar a dimensão
            if vetor_consulta.shape[1] != self.indices[indice_id].d:
                raise ValueError(f"Dimensão do vetor de consulta ({vetor_consulta.shape[1]}) não corresponde ao índice ({self.indices[indice_id].d})")
            
            # Realizar a busca
            D, I = self.indices[indice_id].search(vetor_consulta, k)
            
            # Extrair resultados da primeira consulta
            indices = I[0].tolist()
            scores = D[0].tolist()
            
            return indices, scores
            
        except Exception as e:
            logger.error(f"Erro na busca no índice {indice_id}: {str(e)}")
            return [], []
    
    async def buscar_documentos(self, 
                              indice_id: str, 
                              vetor_consulta: np.ndarray, 
                              k: int = 5) -> List[Tuple[Any, float]]:
        """
        Realiza uma busca e retorna documentos completos com scores.
        
        Args:
            indice_id: ID do índice
            vetor_consulta: Vetor de consulta
            k: Número de resultados a retornar
            
        Returns:
            List[Tuple[Any, float]]: Lista de tuplas (documento, score)
        """
        # Verificar se há mapeamento para este índice
        if indice_id not in self.indices or not self.mapeamentos.get(indice_id):
            logger.error(f"Índice {indice_id} não encontrado ou sem mapeamento")
            return []
        
        try:
            # Realizar a busca
            indices, scores = await self.buscar(indice_id, vetor_consulta, k)
            
            # Mapear para documentos
            resultados = []
            for idx, score in zip(indices, scores):
                if idx != -1 and idx in self.mapeamentos[indice_id]:
                    doc = self.mapeamentos[indice_id][idx]
                    # Converter distância para similaridade
                    similaridade = 1.0 - float(score) / 2.0
                    resultados.append((doc, similaridade))
            
            return resultados
            
        except Exception as e:
            logger.error(f"Erro na busca de documentos no índice {indice_id}: {str(e)}")
            return []
    
    def obter_info_indice(self, indice_id: str) -> Optional[Dict[str, Any]]:
        """
        Obtém informações detalhadas sobre um índice.
        
        Args:
            indice_id: ID do índice
            
        Returns:
            Dict ou None: Informações do índice ou None se não encontrado
        """
        if indice_id not in self.indices:
            return None
        
        try:
            index = self.indices[indice_id]
            metadata = self.metadados.get(indice_id, {})
            
            # Informações básicas
            info = {
                "id": indice_id,
                "tipo": type(index).__name__,
                "dimensao": index.d,
                "num_vetores": index.ntotal,
                "tem_mapeamento": indice_id in self.mapeamentos and bool(self.mapeamentos[indice_id]),
                "num_documentos": len(self.mapeamentos.get(indice_id, {}))
            }
            
            # Adicionar metadados se disponíveis
            if metadata:
                if hasattr(metadata, "dict"):
                    # Se for um modelo Pydantic
                    info.update(metadata.dict())
                else:
                    # Se for um dicionário
                    info.update(metadata)
            
            return info
            
        except Exception as e:
            logger.error(f"Erro ao obter informações do índice {indice_id}: {str(e)}")
            return None
    
    def listar_indices(self) -> List[Dict[str, Any]]:
        """
        Lista todos os índices disponíveis.
        
        Returns:
            List[Dict]: Lista com informações básicas de cada índice
        """
        return [self.obter_info_indice(indice_id) for indice_id in self.indices.keys()]
    
    async def remover_indice(self, indice_id: str) -> bool:
        """
        Remove um índice da memória (não remove arquivos).
        
        Args:
            indice_id: ID do índice
            
        Returns:
            bool: True se removido com sucesso
        """
        if indice_id not in self.indices:
            return False
        
        try:
            # Remover das estruturas em memória
            del self.indices[indice_id]
            if indice_id in self.mapeamentos:
                del self.mapeamentos[indice_id]
            if indice_id in self.metadados:
                del self.metadados[indice_id]
            
            logger.info(f"Índice {indice_id} removido da memória")
            return True
            
        except Exception as e:
            logger.error(f"Erro ao remover índice {indice_id}: {str(e)}")
            return False


# Instância global do serviço
faiss_service = FaissService()

# Função para inicializar o serviço FAISS
async def inicializar_servico_faiss():
    """Inicializa o serviço FAISS."""
    await faiss_service.inicializar()

# Função para obter a instância do serviço
def get_faiss_service() -> FaissService:
    """
    Obtém a instância do serviço FAISS.
    
    Returns:
        FaissService: Instância do serviço
    """
    return faiss_service    