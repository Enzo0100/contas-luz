from fastapi import FastAPI
import logging
import os
from dotenv import load_dotenv

from .api import api_router
from .api.middleware import setup_middlewares
from .api.exceptions import register_exception_handlers
from .config import settings
from .utils.logging_config import setup_logging

# Carregar variáveis de ambiente
load_dotenv()

# Configurar logging
setup_logging()
logger = logging.getLogger("app")

def create_application() -> FastAPI:
    """
    Cria e configura a aplicação FastAPI.
    
    Returns:
        FastAPI: Aplicação configurada
    """
    # Inicializar aplicação
    app = FastAPI(
        title=settings.APP_TITLE,
        description=settings.APP_DESCRIPTION,
        version=settings.APP_VERSION,
        docs_url="/docs" if settings.SHOW_DOCS else None,
        redoc_url="/redoc" if settings.SHOW_DOCS else None,
    )
    
    # Configurar middlewares
    setup_middlewares(app)
    
    # Registrar handlers de exceções
    register_exception_handlers(app)
    
    # Incluir routers
    app.include_router(api_router, prefix=settings.API_PREFIX)
    
    # Registrar eventos
    register_startup_events(app)
    register_shutdown_events(app)
    
    return app

def register_startup_events(app: FastAPI):
    """
    Registra eventos que serão executados na inicialização da aplicação.
    
    Args:
        app: Aplicação FastAPI
    """
    @app.on_event("startup")
    async def startup_event():
        logger.info(f"Iniciando aplicação: {settings.APP_TITLE} v{settings.APP_VERSION}")
        
        # Verificar diretórios necessários
        for directory in [settings.DIRETORIO_DADOS, settings.DIRETORIO_FAISS]:
            if not os.path.exists(directory):
                os.makedirs(directory)
                logger.info(f"Diretório criado: {directory}")
        
        # Inicializar serviços
        from .services.embeddings_service import inicializar_servico_embeddings
        from .services.chat_service import inicializar_servico_chat
        
        await inicializar_servico_embeddings()
        await inicializar_servico_chat()
        
        logger.info("Serviços inicializados com sucesso")

def register_shutdown_events(app: FastAPI):
    """
    Registra eventos que serão executados no encerramento da aplicação.
    
    Args:
        app: Aplicação FastAPI
    """
    @app.on_event("shutdown")
    async def shutdown_event():
        logger.info("Encerrando aplicação")
        
        # Liberação de recursos, se necessário
        # Exemplo: fechar conexões com bancos de dados, etc.

# Criar instância da aplicação
app = create_application()

# Para execução direta
if __name__ == "__main__":
    import uvicorn
    
    # Obter configurações do servidor a partir das variáveis de ambiente
    host = settings.HOST
    port = settings.PORT
    
    logger.info(f"Iniciando servidor em http://{host}:{port}")
    
    # Iniciar servidor
    uvicorn.run(
        "app.main:app", 
        host=host, 
        port=port, 
        reload=settings.DEBUG,
        log_level="info" if settings.DEBUG else "warning"
    )