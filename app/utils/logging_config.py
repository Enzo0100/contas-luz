import logging
import logging.handlers
import os
from datetime import datetime
from ..config import settings

def setup_logging():
    """
    Configura o sistema de logging da aplicação.
    Define formatos, níveis, handlers e filtros.
    """
    # Garantir que o diretório de logs existe
    logs_dir = settings.LOGS_DIR
    os.makedirs(logs_dir, exist_ok=True)
    
    # Configuração do nível de logging
    log_level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)
    
    # Configuração do formato dos logs
    log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    date_format = "%Y-%m-%d %H:%M:%S"
    formatter = logging.Formatter(log_format, date_format)
    
    # Configuração do logger raiz
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    
    # Limpar handlers existentes
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Adicionar um handler para a console
    console_handler = logging.StreamHandler()
    console_handler.setLevel(log_level)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)
    
    # Adicionar um handler para arquivo, com rotação diária
    log_file = os.path.join(logs_dir, f"app_{datetime.now().strftime('%Y%m%d')}.log")
    file_handler = logging.handlers.TimedRotatingFileHandler(
        log_file, when="midnight", interval=1, backupCount=30
    )
    file_handler.setLevel(log_level)
    file_handler.setFormatter(formatter)
    root_logger.addHandler(file_handler)
    
    # Adicionar um handler separado para erros
    error_file = os.path.join(logs_dir, f"errors_{datetime.now().strftime('%Y%m%d')}.log")
    error_handler = logging.handlers.TimedRotatingFileHandler(
        error_file, when="midnight", interval=1, backupCount=30
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(formatter)
    root_logger.addHandler(error_handler)
    
    # Configurar loggers específicos
    if settings.DEBUG:
        # Em modo debug, aumentar o nível de alguns loggers de componentes específicos
        debug_loggers = [
            "app.services.embeddings", 
            "app.services.faiss", 
            "app.services.chat",
            "app.api"
        ]
        for logger_name in debug_loggers:
            logger = logging.getLogger(logger_name)
            logger.setLevel(logging.DEBUG)
    else:
        # Em produção, reduzir o log de algumas bibliotecas verbosas
        silent_loggers = [
            "openai",
            "httpx",
            "faiss"
        ]
        for logger_name in silent_loggers:
            logger = logging.getLogger(logger_name)
            logger.setLevel(logging.WARNING)
    
    # Silenciar alguns loggers específicos independente do modo
    logging.getLogger("httpx").setLevel(logging.WARNING)
    
    # Log de inicialização do sistema de logging
    root_logger.info(f"Sistema de logging inicializado (nível: {settings.LOG_LEVEL})")
    
    return root_logger

class RequestIdFilter(logging.Filter):
    """
    Filtro para adicionar o ID de requisição aos logs.
    """
    def __init__(self, name="", request_id=None):
        super().__init__(name)
        self.request_id = request_id

    def filter(self, record):
        record.request_id = getattr(record, "request_id", self.request_id or "no_request_id")
        return True
