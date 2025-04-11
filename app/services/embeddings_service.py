import os
import json
import time
import hashlib
import logging
import numpy as np
from typing import Dict, List, Any, Optional, Tuple, Union
from datetime import datetime
from openai import OpenAI
import faiss

from ..models.embeddings import (
    DocumentoBase,
    ClienteDocumento,
    FaturaDocumento,
    AnaliseDocumento,
    DocumentoEmbedding,
    EmbeddingCache,
    IndiceMetadata
)
from ..models.database import db
from ..config import settings

# Configuração de logging
logger = logging.getLogger("services.embeddings")

class EmbeddingsService:
    """
    Serviço para geração de embeddings e gerenciamento do FAISS.
    Responsável por:
    - Gerar embeddings usando OpenAI
    - Manter um cache de embeddings
    - Gerenciar índices FAISS para busca por similaridade
    """
    
    def __init__(self):
        """Inicializa o serviço de embeddings."""
        # Configurações
        self.api_key = settings.OPENAI_API_KEY
        self.modelo_embeddings = settings.MODELO_EMBEDDINGS
        self.dimensao_embeddings = settings.DIMENSAO_EMBEDDINGS
        self.diretorio_faiss = settings.DIRETORIO_FAISS
        self.diretorio_cache = os.path.join(settings.DATA_DIR, "embeddings_cache")
        
        # Garantir que diretórios existam
        os.makedirs(self.diretorio_faiss, exist_ok=True)
        os.makedirs(self.diretorio_cache, exist_ok=True)
        
        # Cliente OpenAI
        self.client = OpenAI(api_key=self.api_key)
        
        # Cache de embeddings
        self.cache_embeddings = {}
        
        # Índice FAISS
        self.index = None
        self.indice_metadata = None
        self.id_para_documento = {}
        
        # Flag de inicialização
        self.inicializado = False
        
        logger.info(f"Serviço de embeddings criado com modelo: {self.modelo_embeddings}")
    
    async def inicializar(self):
        """Inicializa o serviço, carregando cache e índice FAISS."""
        if self.inicializado:
            return
        
        logger.info("Inicializando serviço de embeddings...")
        
        # Carregar cache de embeddings
        await self.carregar_cache()
        
        # Tentar carregar índice FAISS existente
        if not await self.carregar_indice_faiss():
            logger.warning("Nenhum índice FAISS encontrado. Será necessário construir um novo.")
        
        self.inicializado = True
        logger.info("Serviço de embeddings inicializado")
    
    async def carregar_cache(self):
        """Carrega o cache de embeddings dos arquivos."""
        try:
            # Listar arquivos de cache
            arquivos_cache = [f for f in os.listdir(self.diretorio_cache) if f.endswith('.json')]
            count = 0
            
            for arquivo in arquivos_cache:
                try:
                    with open(os.path.join(self.diretorio_cache, arquivo), 'r', encoding='utf-8') as f:
                        cache_data = json.load(f)
                        
                    # Processar cada entrada do cache
                    for chave, dados in cache_data.items():
                        self.cache_embeddings[chave] = np.array(dados["embedding"], dtype=np.float32)
                        count += 1
                        
                except Exception as e:
                    logger.error(f"Erro ao carregar arquivo de cache {arquivo}: {str(e)}")
            
            logger.info(f"Cache de embeddings carregado: {count} entradas")
            
        except Exception as e:
            logger.error(f"Erro ao carregar cache de embeddings: {str(e)}")
    
    async def salvar_cache(self):
        """Salva o cache de embeddings em arquivo."""
        try:
            # Preparar dados para salvar
            cache_data = {}
            timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
            
            for chave, embedding in self.cache_embeddings.items():
                cache_data[chave] = {
                    "embedding": embedding.tolist() if isinstance(embedding, np.ndarray) else embedding,
                    "modelo": self.modelo_embeddings,
                    "timestamp": datetime.now().isoformat()
                }
            
            # Salvar em arquivo
            caminho_cache = os.path.join(self.diretorio_cache, f"embeddings_cache_{timestamp}.json")
            with open(caminho_cache, 'w', encoding='utf-8') as f:
                json.dump(cache_data, f, ensure_ascii=False)
            
            logger.info(f"Cache de embeddings salvo: {len(cache_data)} entradas")
            
        except Exception as e:
            logger.error(f"Erro ao salvar cache de embeddings: {str(e)}")
    
    async def gerar_embedding(self, texto: str) -> np.ndarray:
        """
        Gera um embedding para um texto usando a OpenAI.
        Usa cache quando disponível.
        
        Args:
            texto: Texto para gerar embedding
            
        Returns:
            np.ndarray: Vetor de embedding
        """
        # Gerar hash do texto para chave de cache
        texto_hash = hashlib.md5(texto.encode()).hexdigest()
        chave_cache = f"{texto_hash}_{self.modelo_embeddings}"
        
        # Verificar se está no cache
        if chave_cache in self.cache_embeddings:
            return self.cache_embeddings[chave_cache]
        
        try:
            # Chamar API da OpenAI
            logger.debug(f"Gerando embedding para texto de {len(texto)} caracteres")
            response = self.client.embeddings.create(
                model=self.modelo_embeddings,
                input=[texto]
            )
            
            # Extrair o embedding e converter para numpy
            embedding = np.array(response.data[0].embedding, dtype=np.float32)
            
            # Armazenar no cache
            self.cache_embeddings[chave_cache] = embedding
            
            # Salvar cache periodicamente (a cada 10 novas entradas)
            if len(self.cache_embeddings) % 10 == 0:
                await self.salvar_cache()
            
            return embedding
            
        except Exception as e:
            logger.error(f"Erro ao gerar embedding: {str(e)}")
            # Retornar vetor de zeros em caso de erro
            return np.zeros(self.dimensao_embeddings, dtype=np.float32)
    
    async def gerar_embeddings_batch(self, textos: List[str]) -> List[np.ndarray]:
        """
        Gera embeddings para vários textos em lote.
        Aproveita o cache quando possível.
        
        Args:
            textos: Lista de textos para gerar embeddings
            
        Returns:
            List[np.ndarray]: Lista de vetores de embedding
        """
        # Preparar lotes para processamento
        embeddings = []
        textos_para_processar = []
        indices_para_processar = []
        
        # Verificar quais textos já estão em cache
        for i, texto in enumerate(textos):
            texto_hash = hashlib.md5(texto.encode()).hexdigest()
            chave_cache = f"{texto_hash}_{self.modelo_embeddings}"
            
            if chave_cache in self.cache_embeddings:
                # Usar embedding do cache
                embeddings.append(self.cache_embeddings[chave_cache])
            else:
                # Marcar para processamento
                textos_para_processar.append(texto)
                indices_para_processar.append(i)
                # Reservar espaço no resultado (será preenchido depois)
                embeddings.append(None)
        
        # Se há textos para processar
        if textos_para_processar:
            try:
                logger.info(f"Gerando embeddings para lote de {len(textos_para_processar)} textos")
                
                # Chamar API da OpenAI
                response = self.client.embeddings.create(
                    model=self.modelo_embeddings,
                    input=textos_para_processar
                )
                
                # Processar resultados
                for i, embed_data in enumerate(response.data):
                    idx = indices_para_processar[i]
                    texto = textos_para_processar[i]
                    
                    # Converter para numpy
                    embedding = np.array(embed_data.embedding, dtype=np.float32)
                    
                    # Armazenar no cache
                    texto_hash = hashlib.md5(texto.encode()).hexdigest()
                    chave_cache = f"{texto_hash}_{self.modelo_embeddings}"
                    self.cache_embeddings[chave_cache] = embedding
                    
                    # Atualizar no resultado
                    embeddings[idx] = embedding
                
                # Salvar cache
                await self.salvar_cache()
                
            except Exception as e:
                logger.error(f"Erro ao gerar embeddings em lote: {str(e)}")
                
                # Preencher com zeros os que não foram processados
                for idx in indices_para_processar:
                    if embeddings[idx] is None:
                        embeddings[idx] = np.zeros(self.dimensao_embeddings, dtype=np.float32)
        
        return embeddings
    
    async def construir_indice_faiss(self, documentos: List[DocumentoEmbedding], nome_indice: str = None) -> bool:
        """
        Constrói um índice FAISS a partir de documentos com embeddings.
        
        Args:
            documentos: Lista de documentos com embeddings
            nome_indice: Nome opcional para o índice
            
        Returns:
            bool: True se construído com sucesso
        """
        if not documentos:
            logger.warning("Nenhum documento fornecido para construir o índice FAISS")
            return False
        
        try:
            # Extrair embeddings para matriz
            embeddings = []
            id_para_documento = {}
            
            for i, doc in enumerate(documentos):
                if doc.embedding is not None:
                    embeddings.append(doc.embedding)
                    id_para_documento[i] = doc.documento
            
            if not embeddings:
                logger.warning("Nenhum embedding válido para construir o índice FAISS")
                return False
            
            # Converter para matriz numpy
            embeddings_matrix = np.array(embeddings, dtype=np.float32)
            
            # Criar índice FAISS
            dimension = embeddings_matrix.shape[1]
            self.index = faiss.IndexFlatL2(dimension)
            
            # Adicionar vetores ao índice
            self.index.add(embeddings_matrix)
            
            # Atualizar mapeamento de IDs
            self.id_para_documento = id_para_documento
            
            # Criar metadata do índice
            indice_id = nome_indice or f"indice_{datetime.now().strftime('%Y%m%d%H%M%S')}"
            self.indice_metadata = IndiceMetadata(
                id=indice_id,
                nome=nome_indice or f"Índice FAISS {datetime.now().strftime('%d/%m/%Y %H:%M')}",
                dimensao=dimension,
                modelo_embeddings=self.modelo_embeddings,
                num_vetores=len(embeddings),
                data_criacao=datetime.now(),
                ultima_atualizacao=datetime.now(),
                tem_mapeamento_ids=True
            )
            
            # Salvar índice
            await self.salvar_indice_faiss()
            
            logger.info(f"Índice FAISS construído com {len(embeddings)} vetores de dimensão {dimension}")
            return True
            
        except Exception as e:
            logger.error(f"Erro ao construir índice FAISS: {str(e)}")
            return False
    
    async def salvar_indice_faiss(self) -> bool:
        """
        Salva o índice FAISS em disco.
        
        Returns:
            bool: True se salvo com sucesso
        """
        if self.index is None or self.indice_metadata is None:
            logger.warning("Nenhum índice FAISS para salvar")
            return False
        
        try:
            # Criar nome de arquivo com timestamp
            timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
            indice_id = self.indice_metadata.id
            
            # Caminho para o arquivo do índice
            caminho_indice = os.path.join(self.diretorio_faiss, f"{indice_id}_{timestamp}.index")
            
            # Salvar índice FAISS
            faiss.write_index(self.index, caminho_indice)
            
            # Salvar mapeamento de IDs
            caminho_mapeamento = os.path.join(self.diretorio_faiss, f"{indice_id}_{timestamp}_mapping.json")
            
            # Converter o mapeamento para formato serializável
            mapeamento_serializavel = {}
            for idx, doc in self.id_para_documento.items():
                # Se for um modelo Pydantic
                if hasattr(doc, "dict"):
                    mapeamento_serializavel[str(idx)] = doc.dict()
                else:
                    # Caso seja outro tipo de objeto
                    mapeamento_serializavel[str(idx)] = doc
            
            with open(caminho_mapeamento, 'w', encoding='utf-8') as f:
                json.dump(mapeamento_serializavel, f, ensure_ascii=False, indent=2)
            
            # Salvar metadados
            self.indice_metadata.ultima_atualizacao = datetime.now()
            caminho_metadata = os.path.join(self.diretorio_faiss, f"{indice_id}_{timestamp}_metadata.json")
            
            with open(caminho_metadata, 'w', encoding='utf-8') as f:
                json.dump(self.indice_metadata.dict(), f, ensure_ascii=False, indent=2)
            
            logger.info(f"Índice FAISS salvo em {caminho_indice}")
            return True
            
        except Exception as e:
            logger.error(f"Erro ao salvar índice FAISS: {str(e)}")
            return False
    
    async def carregar_indice_faiss(self, caminho_indice: str = None) -> bool:
        """
        Carrega um índice FAISS do disco.
        
        Args:
            caminho_indice: Caminho específico para o arquivo do índice ou None para carregar o mais recente
            
        Returns:
            bool: True se carregado com sucesso
        """
        try:
            # Se não for especificado um caminho, buscar o índice mais recente
            if not caminho_indice:
                arquivos_indice = [f for f in os.listdir(self.diretorio_faiss) if f.endswith('.index')]
                if not arquivos_indice:
                    logger.warning("Nenhum arquivo de índice FAISS encontrado")
                    return False
                
                # Ordenar por data (presumindo formato de nome específico)
                arquivos_indice.sort(reverse=True)
                caminho_indice = os.path.join(self.diretorio_faiss, arquivos_indice[0])
                
                # Extrair prefixo do nome do arquivo para buscar outros arquivos relacionados
                prefixo = arquivos_indice[0].split('_')[0]
                
                # Buscar arquivo de mapeamento
                arquivos_mapeamento = [f for f in os.listdir(self.diretorio_faiss) 
                                     if f.startswith(prefixo) and f.endswith('_mapping.json')]
                
                if arquivos_mapeamento:
                    arquivos_mapeamento.sort(reverse=True)
                    caminho_mapeamento = os.path.join(self.diretorio_faiss, arquivos_mapeamento[0])
                else:
                    caminho_mapeamento = None
                
                # Buscar arquivo de metadata
                arquivos_metadata = [f for f in os.listdir(self.diretorio_faiss) 
                                   if f.startswith(prefixo) and f.endswith('_metadata.json')]
                
                if arquivos_metadata:
                    arquivos_metadata.sort(reverse=True)
                    caminho_metadata = os.path.join(self.diretorio_faiss, arquivos_metadata[0])
                else:
                    caminho_metadata = None
            else:
                # Se um caminho específico for fornecido, derivar os outros
                base_name = os.path.basename(caminho_indice).replace('.index', '')
                dir_name = os.path.dirname(caminho_indice)
                
                caminho_mapeamento = os.path.join(dir_name, f"{base_name}_mapping.json")
                if not os.path.exists(caminho_mapeamento):
                    caminho_mapeamento = None
                
                caminho_metadata = os.path.join(dir_name, f"{base_name}_metadata.json")
                if not os.path.exists(caminho_metadata):
                    caminho_metadata = None
            
            # Carregar o índice FAISS
            self.index = faiss.read_index(caminho_indice)
            
            # Carregar o mapeamento de IDs se existir
            if caminho_mapeamento and os.path.exists(caminho_mapeamento):
                with open(caminho_mapeamento, 'r', encoding='utf-8') as f:
                    mapeamento_raw = json.load(f)
                
                # Converter as chaves para inteiros
                self.id_para_documento = {int(k): v for k, v in mapeamento_raw.items()}
            else:
                self.id_para_documento = {}
            
            # Carregar metadados se existirem
            if caminho_metadata and os.path.exists(caminho_metadata):
                with open(caminho_metadata, 'r', encoding='utf-8') as f:
                    metadata_raw = json.load(f)
                
                self.indice_metadata = IndiceMetadata(**metadata_raw)
            else:
                # Criar metadados básicos
                self.indice_metadata = IndiceMetadata(
                    id=f"indice_carregado_{datetime.now().strftime('%Y%m%d%H%M%S')}",
                    nome=f"Índice carregado em {datetime.now().strftime('%d/%m/%Y %H:%M')}",
                    dimensao=self.index.d,
                    modelo_embeddings=self.modelo_embeddings,
                    num_vetores=self.index.ntotal,
                    data_criacao=datetime.now(),
                    ultima_atualizacao=datetime.now(),
                    tem_mapeamento_ids=(len(self.id_para_documento) > 0)
                )
            
            logger.info(f"Índice FAISS carregado: {self.index.ntotal} vetores de dimensão {self.index.d}")
            return True
            
        except Exception as e:
            logger.error(f"Erro ao carregar índice FAISS: {str(e)}")
            return False
    
    async def buscar(self, 
                   texto_consulta: str, 
                   k: int = 5,
                   filtro: Optional[Dict[str, Any]] = None) -> List[Tuple[Any, float]]:
        """
        Realiza uma busca por similaridade no índice FAISS.
        
        Args:
            texto_consulta: Texto da consulta
            k: Número de resultados a retornar
            filtro: Dicionário com filtros a aplicar nos resultados
            
        Returns:
            List[Tuple[Any, float]]: Lista de tuplas (documento, score de similaridade)
        """
        if self.index is None:
            logger.error("Índice FAISS não inicializado")
            return []
        
        try:
            # Gerar embedding para a consulta
            embedding_consulta = await self.gerar_embedding(texto_consulta)
            
            # Formatar como matriz para o FAISS
            query_vector = np.array([embedding_consulta], dtype=np.float32)
            
            # Buscar no índice
            distances, indices = self.index.search(query_vector, k)
            
            # Preparar resultados
            resultados = []
            
            for i, idx in enumerate(indices[0]):
                # Verificar se é um índice válido
                if idx == -1 or idx not in self.id_para_documento:
                    continue
                
                doc = self.id_para_documento[idx]
                score = 1.0 - float(distances[0][i]) / 2.0  # Converter distância para similaridade
                
                # Aplicar filtros se especificados
                if filtro:
                    atende_filtro = True
                    for chave, valor in filtro.items():
                        if hasattr(doc, chave):
                            if getattr(doc, chave) != valor:
                                atende_filtro = False
                                break
                        elif chave in doc:
                            if doc[chave] != valor:
                                atende_filtro = False
                                break
                        else:
                            # Se não encontrar a chave, assume que não atende o filtro
                            atende_filtro = False
                            break
                    
                    if not atende_filtro:
                        continue
                
                resultados.append((doc, score))
            
            return resultados
            
        except Exception as e:
            logger.error(f"Erro na busca por similaridade: {str(e)}")
            return []
    
    async def buscar_cliente_por_matricula(self, matricula: str) -> Optional[Dict[str, Any]]:
        """
        Busca informações de um cliente por matrícula.
        
        Args:
            matricula: Matrícula do cliente
            
        Returns:
            Dict ou None: Dados do cliente ou None se não encontrado
        """
        try:
            # Primeiro tenta buscar em dados estruturados (sem usar embeddings)
            # Isso é mais rápido para busca exata por matrícula
            clientes = db.buscar_documentos("clientes", {"numeroCliente": matricula})
            
            if clientes and len(clientes) > 0:
                return clientes[0]
            
            # Se não encontrou, tenta usar FAISS com uma consulta específica
            if self.index is not None:
                consulta = f"Informações do cliente com matrícula {matricula}"
                resultados = await self.buscar(
                    texto_consulta=consulta,
                    k=5,
                    filtro={"tipo": "cliente_info"}
                )
                
                for doc, score in resultados:
                    # Verificar se é o cliente certo
                    if hasattr(doc, "matricula") and doc.matricula == matricula:
                        return doc
                    elif isinstance(doc, dict) and doc.get("matricula") == matricula:
                        return doc
            
            return None
            
        except Exception as e:
            logger.error(f"Erro ao buscar cliente por matrícula: {str(e)}")
            return None
    
    async def buscar_faturas_cliente(self, cliente_id: str) -> List[Dict[str, Any]]:
        """
        Busca faturas de um cliente específico.
        
        Args:
            cliente_id: ID do cliente
            
        Returns:
            List[Dict]: Lista de faturas do cliente
        """
        try:
            # Buscar diretamente no banco de dados
            faturas = db.buscar_documentos("faturas", {"cliente_id": cliente_id})
            
            if faturas:
                return faturas
            
            # Se não encontrou, tenta usar FAISS
            if self.index is not None:
                consulta = f"Faturas do cliente {cliente_id}"
                resultados = await self.buscar(
                    texto_consulta=consulta,
                    k=20,  # Buscar mais resultados para garantir
                    filtro={"tipo": "fatura", "cliente_id": cliente_id}
                )
                
                return [doc for doc, score in resultados]
            
            return []
            
        except Exception as e:
            logger.error(f"Erro ao buscar faturas do cliente: {str(e)}")
            return []


# Instância global do serviço
embeddings_service = EmbeddingsService()

# Função para inicializar o serviço de embeddings
async def inicializar_servico_embeddings():
    """Inicializa o serviço de embeddings."""
    await embeddings_service.inicializar()

# Função para obter a instância do serviço
def get_embeddings_service() -> EmbeddingsService:
    """
    Obtém a instância do serviço de embeddings.
    
    Returns:
        EmbeddingsService: Instância do serviço
    """
    return embeddings_service