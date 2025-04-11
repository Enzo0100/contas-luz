from fastapi import APIRouter
from .routes import router as consulta_router

# Criar o router principal da API
api_router = APIRouter()

# Incluir sub-routers
api_router.include_router(consulta_router, prefix="/consulta")

# Outros routers podem ser adicionados aqui
# Exemplo:
# from .admin import router as admin_router
# api_router.include_router(admin_router, prefix="/admin", tags=["admin"])

# Exportar routers
__all__ = ["api_router"]