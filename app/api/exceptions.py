from fastapi import Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
import logging
from typing import Any, Dict, Optional

# Configuração de logging
logger = logging.getLogger("api.exceptions")

# Classes de exceções customizadas
class APIException(Exception):
    """
    Exceção base para erros da API.
    Facilita o tratamento consistente de erros.
    """
    
    def __init__(
        self, 
        message: str, 
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
        code: str = "internal_error",
        details: Optional[Dict[str, Any]] = None
    ):
        self.message = message
        self.status_code = status_code
        self.code = code
        self.details = details or {}
        super().__init__(self.message)

class NotFoundException(APIException):
    """Exceção para recursos não encontrados."""
    
    def __init__(
        self, 
        message: str = "Recurso não encontrado", 
        code: str = "not_found",
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=message,
            status_code=status.HTTP_404_NOT_FOUND,
            code=code,
            details=details
        )

class UnauthorizedException(APIException):
    """Exceção para requisições não autorizadas."""
    
    def __init__(
        self, 
        message: str = "Acesso não autorizado", 
        code: str = "unauthorized",
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=message,
            status_code=status.HTTP_401_UNAUTHORIZED,
            code=code,
            details=details
        )

class ForbiddenException(APIException):
    """Exceção para acesso proibido."""
    
    def __init__(
        self, 
        message: str = "Acesso proibido", 
        code: str = "forbidden",
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=message,
            status_code=status.HTTP_403_FORBIDDEN,
            code=code,
            details=details
        )

class BadRequestException(APIException):
    """Exceção para requisições inválidas."""
    
    def __init__(
        self, 
        message: str = "Requisição inválida", 
        code: str = "bad_request",
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=message,
            status_code=status.HTTP_400_BAD_REQUEST,
            code=code,
            details=details
        )

class RateLimitException(APIException):
    """Exceção para limite de requisições excedido."""
    
    def __init__(
        self, 
        message: str = "Limite de requisições excedido", 
        code: str = "rate_limit_exceeded",
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=message,
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            code=code,
            details=details
        )

class ServiceUnavailableException(APIException):
    """Exceção para serviço indisponível."""
    
    def __init__(
        self, 
        message: str = "Serviço temporariamente indisponível", 
        code: str = "service_unavailable",
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=message,
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            code=code,
            details=details
        )

# Handlers para tratamento de exceções
async def api_exception_handler(request: Request, exc: APIException):
    """
    Handler para as exceções da API.
    
    Args:
        request: Objeto da requisição
        exc: Exceção da API
    
    Returns:
        JSONResponse com detalhes do erro
    """
    logger.error(
        f"API Exception: {exc.code} - {exc.message} - Status: {exc.status_code}"
    )
    
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "code": exc.code,
            "message": exc.message,
            "details": exc.details,
            "path": request.url.path
        }
    )

async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    """
    Handler para as exceções HTTP do Starlette.
    
    Args:
        request: Objeto da requisição
        exc: Exceção HTTP
    
    Returns:
        JSONResponse com detalhes do erro
    """
    logger.error(
        f"HTTP Exception: {exc.status_code} - {exc.detail}"
    )
    
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "code": f"http_{exc.status_code}",
            "message": exc.detail,
            "path": request.url.path
        }
    )

async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """
    Handler para as exceções de validação de requests.
    
    Args:
        request: Objeto da requisição
        exc: Exceção de validação
    
    Returns:
        JSONResponse com detalhes do erro de validação
    """
    # Formatar mensagem de erro de validação
    error_messages = []
    for error in exc.errors():
        location = " -> ".join([str(loc) for loc in error["loc"] if loc != "body"])
        message = error["msg"]
        error_messages.append(f"{location}: {message}")
    
    error_detail = ", ".join(error_messages)
    logger.warning(f"Validation Error: {error_detail}")
    
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "code": "validation_error",
            "message": "Erro de validação dos dados da requisição",
            "details": {
                "errors": exc.errors()
            },
            "path": request.url.path
        }
    )

async def generic_exception_handler(request: Request, exc: Exception):
    """
    Handler genérico para exceções não tratadas.
    
    Args:
        request: Objeto da requisição
        exc: Exceção
    
    Returns:
        JSONResponse com detalhes do erro
    """
    # Registrar a exceção completa para debugging
    logger.exception(f"Unhandled Exception: {str(exc)}")
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "code": "internal_server_error",
            "message": "Ocorreu um erro interno no servidor",
            "path": request.url.path
        }
    )

# Função para registrar todos os handlers de exceção na aplicação
def register_exception_handlers(app):
    """
    Registra todos os handlers de exceções na aplicação FastAPI.
    
    Args:
        app: Aplicação FastAPI
    """
    # Handler para APIException e subclasses
    app.add_exception_handler(APIException, api_exception_handler)
    
    # Handler para exceções HTTP do Starlette
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    
    # Handler para erros de validação
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    
    # Handler para exceções genéricas não tratadas
    app.add_exception_handler(Exception, generic_exception_handler)