from fastapi import Request, Response
from fastapi.middleware.base import BaseHTTPMiddleware
from starlette.middleware.cors import CORSMiddleware
from typing import Callable, Dict
import time
import logging
import json
from datetime import datetime
import uuid

# Configuração de logging
logger = logging.getLogger("api.middleware")

class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware para registrar informações sobre requisições e respostas.
    Ajuda no monitoramento e depuração da API.
    """
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Gerar ID único para a requisição
        request_id = str(uuid.uuid4())
        
        # Registrar início da requisição
        start_time = time.time()
        
        # Adicionar request_id aos headers
        request.state.request_id = request_id
        
        # Coletar informações básicas da requisição
        request_info = {
            "request_id": request_id,
            "method": request.method,
            "url": str(request.url),
            "client": request.client.host if request.client else "unknown",
            "timestamp": datetime.now().isoformat(),
        }
        
        # Registrar informações da requisição
        logger.info(f"Recebida requisição: {json.dumps(request_info)}")
        
        # Processar a requisição
        try:
            response = await call_next(request)
            
            # Calcular tempo de processamento
            process_time = time.time() - start_time
            
            # Adicionar request_id e tempo de processamento à resposta
            response.headers["X-Request-ID"] = request_id
            response.headers["X-Process-Time"] = str(process_time)
            
            # Registrar informações da resposta
            logger.info(
                f"Resposta enviada: status={response.status_code}, "
                f"request_id={request_id}, process_time={process_time:.4f}s"
            )
            
            return response
            
        except Exception as e:
            # Registrar erro
            logger.error(
                f"Erro ao processar requisição: request_id={request_id}, error={str(e)}"
            )
            
            # Repassar exceção
            raise

class RateLimitingMiddleware(BaseHTTPMiddleware):
    """
    Middleware para limitar a taxa de requisições por cliente.
    Previne abusos e sobrecarga da API.
    """
    
    def __init__(self, app, requests_per_minute: int = 100):
        super().__init__(app)
        self.requests_per_minute = requests_per_minute
        self.client_requests: Dict[str, Dict] = {}
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Obter IP do cliente
        client_ip = request.client.host if request.client else "unknown"
        
        # Timestamp atual
        current_time = time.time()
        
        # Verificar se cliente já está no registro
        if client_ip in self.client_requests:
            client_data = self.client_requests[client_ip]
            
            # Limpar requisições antigas (mais de 1 minuto)
            client_data["timestamps"] = [
                ts for ts in client_data["timestamps"] if current_time - ts < 60
            ]
            
            # Verificar se ultrapassou o limite
            if len(client_data["timestamps"]) >= self.requests_per_minute:
                logger.warning(f"Rate limit excedido para cliente: {client_ip}")
                
                # Retornar resposta 429 Too Many Requests
                return Response(
                    content=json.dumps({
                        "detail": "Limite de requisições excedido. Tente novamente em alguns minutos."
                    }),
                    status_code=429,
                    media_type="application/json"
                )
            
            # Registrar requisição atual
            client_data["timestamps"].append(current_time)
            
        else:
            # Registrar primeiro acesso do cliente
            self.client_requests[client_ip] = {
                "timestamps": [current_time]
            }
        
        # Processar requisição normalmente
        return await call_next(request)

class APIKeyMiddleware(BaseHTTPMiddleware):
    """
    Middleware para validar chaves de API para endpoints restritos.
    Util para rotas administrativas ou integração com outros sistemas.
    """
    
    def __init__(self, app, api_key: str, protected_paths: list = None):
        super().__init__(app)
        self.api_key = api_key
        self.protected_paths = protected_paths or ["/admin/", "/api/v1/admin/"]
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        path = request.url.path
        
        # Verificar se o path está protegido
        is_protected = any(path.startswith(p) for p in self.protected_paths)
        
        if is_protected:
            # Verificar se a API key está presente
            api_key = request.headers.get("X-API-Key")
            
            if not api_key or api_key != self.api_key:
                logger.warning(f"Tentativa de acesso não autorizado ao path {path}")
                
                # Retornar resposta 401 Unauthorized
                return Response(
                    content=json.dumps({
                        "detail": "Acesso não autorizado. API key inválida ou não fornecida."
                    }),
                    status_code=401,
                    media_type="application/json"
                )
        
        return await call_next(request)

# Função para adicionar todos os middlewares à aplicação
def setup_middlewares(app):
    """
    Configura todos os middlewares para a aplicação FastAPI.
    
    Args:
        app: Aplicação FastAPI
    """
    # Middleware CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Em produção, especifique as origens permitidas
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Middleware para logging de requisições
    app.add_middleware(RequestLoggingMiddleware)
    
    # Middleware para rate limiting
    app.add_middleware(RateLimitingMiddleware, requests_per_minute=100)
    
    # Middleware para validação de API key
    # Descomente para ativar
    # from ..config import settings
    # app.add_middleware(APIKeyMiddleware, api_key=settings.API_KEY)