import re
import hashlib
import json
from datetime import datetime, timedelta
from typing import Dict, List, Any, Tuple, Optional, Union
import logging

# Configuração de logging
logger = logging.getLogger("utils.helpers")

def hash_texto(texto: str) -> str:
    """
    Gera um hash MD5 de um texto.
    
    Args:
        texto: Texto para gerar hash
        
    Returns:
        str: Hash MD5 do texto
    """
    return hashlib.md5(texto.encode('utf-8')).hexdigest()

def normalizar_texto(texto: str) -> str:
    """
    Normaliza um texto para processamento.
    Remove espaços extras, converte para minúsculas, etc.
    
    Args:
        texto: Texto para normalizar
        
    Returns:
        str: Texto normalizado
    """
    # Converter para minúsculas
    texto = texto.lower()
    
    # Remover caracteres especiais e acentos (opcional)
    # texto = unicodedata.normalize('NFKD', texto).encode('ASCII', 'ignore').decode('ASCII')
    
    # Remover espaços extras
    texto = re.sub(r'\s+', ' ', texto).strip()
    
    return texto

def extrair_periodo_texto(texto: str) -> Tuple[datetime, datetime]:
    """
    Extrai período de datas a partir de texto em linguagem natural.
    
    Args:
        texto: Texto com menção a período
        
    Returns:
        Tuple[datetime, datetime]: Data inicial e final do período
    """
    hoje = datetime.now()
    data_inicial = hoje
    data_final = hoje
    
    # Verificar se menciona "último mês"
    if re.search(r'(último|passado|anterior)\s+mês', texto, re.IGNORECASE):
        mes_anterior = hoje.replace(day=1) - timedelta(days=1)
        data_inicial = mes_anterior.replace(day=1)
        data_final = mes_anterior
    
    # Verificar se menciona "últimos X meses"
    match = re.search(r'últimos\s+(\d+)\s+meses', texto, re.IGNORECASE)
    if match:
        num_meses = int(match.group(1))
        data_inicial = hoje.replace(day=1) - timedelta(days=30*num_meses)
        data_final = hoje
    
    # Verificar se menciona "último ano"
    if re.search(r'(último|passado|anterior)\s+ano', texto, re.IGNORECASE):
        ano_anterior = hoje.year - 1
        data_inicial = datetime(ano_anterior, 1, 1)
        data_final = datetime(ano_anterior, 12, 31)
    
    # Verificar se menciona um mês específico
    meses = {
        'janeiro': 1, 'fevereiro': 2, 'março': 3, 'abril': 4, 'maio': 5, 'junho': 6,
        'julho': 7, 'agosto': 8, 'setembro': 9, 'outubro': 10, 'novembro': 11, 'dezembro': 12
    }
    
    for mes_nome, mes_num in meses.items():
        if mes_nome in texto.lower():
            # Verificar se tem ano específico
            match_ano = re.search(r'\b(\d{4})\b', texto)
            ano = int(match_ano.group(1)) if match_ano else hoje.year
            
            # Criar datas inicial e final do mês
            data_inicial = datetime(ano, mes_num, 1)
            
            # Último dia do mês
            if mes_num == 12:
                data_final = datetime(ano, 12, 31)
            else:
                data_final = datetime(ano, mes_num + 1, 1) - timedelta(days=1)
    
    # Retornar o período encontrado
    return data_inicial, data_final

def formatar_numero(valor: float, decimais: int = 2, separador_milhar: bool = True) -> str:
    """
    Formata um número para exibição.
    
    Args:
        valor: Valor a ser formatado
        decimais: Número de casas decimais
        separador_milhar: Se deve usar separador de milhar
        
    Returns:
        str: Valor formatado
    """
    if separador_milhar:
        return f"{valor:,.{decimais}f}".replace(",", "X").replace(".", ",").replace("X", ".")
    else:
        return f"{valor:.{decimais}f}".replace(".", ",")

def formatar_data(data: datetime, formato: str = "%d/%m/%Y") -> str:
    """
    Formata uma data para exibição.
    
    Args:
        data: Data a ser formatada
        formato: Formato de saída
        
    Returns:
        str: Data formatada
    """
    return data.strftime(formato)

def extrair_mes_referencia(texto: str) -> Optional[str]:
    """
    Extrai o mês de referência de um texto.
    
    Args:
        texto: Texto para extrair o mês de referência
        
    Returns:
        str ou None: Mês de referência no formato MM/AAAA ou None se não encontrado
    """
    # Padrão para MM/AAAA
    padrao_mes_ano = re.compile(r'(\d{1,2})/(\d{4})')
    match = padrao_mes_ano.search(texto)
    
    if match:
        mes, ano = match.groups()
        return f"{int(mes):02d}/{ano}"
    
    # Padrão para mês por extenso
    meses = {
        'janeiro': '01', 'fevereiro': '02', 'março': '03', 'abril': '04',
        'maio': '05', 'junho': '06', 'julho': '07', 'agosto': '08',
        'setembro': '09', 'outubro': '10', 'novembro': '11', 'dezembro': '12'
    }
    
    # Buscar mês por extenso seguido de ano
    for mes_nome, mes_num in meses.items():
        padrao = re.compile(f'{mes_nome}\s+de\s+(\d{{4}})', re.IGNORECASE)
        match = padrao.search(texto)
        
        if match:
            ano = match.group(1)
            return f"{mes_num}/{ano}"
    
    return None

def classificar_tipo_consulta(texto: str) -> str:
    """
    Classifica o tipo de consulta em linguagem natural.
    
    Args:
        texto: Texto da consulta
        
    Returns:
        str: Tipo de consulta (consumo, gasto, comparacao, previsao, geral)
    """
    texto_norm = normalizar_texto(texto)
    
    # Verificar consumo
    if re.search(r'(consumo|consumiu|kwh|kw/h|quilowatt)', texto_norm):
        return "consumo"
    
    # Verificar gasto/valor
    if re.search(r'(gasto|gastei|valor|custo|paguei|conta|fatura|dinheiro|reais|\br\$)', texto_norm):
        return "gasto"
    
    # Verificar comparação
    if re.search(r'(compar|diferença|mais que|menos que|aumento|diminuição|variação)', texto_norm):
        return "comparacao"
    
    # Verificar previsão
    if re.search(r'(previs|prever|estimativa|estimar|próximo|futuro|expectativa)', texto_norm):
        return "previsao"
    
    # Consulta geral
    return "geral"

def extrair_dados_visuais(dados: Dict[str, Any], tipo_consulta: str) -> Dict[str, Any]:
    """
    Extrai dados para visualização a partir dos dados da consulta.
    
    Args:
        dados: Dados da consulta
        tipo_consulta: Tipo de consulta
        
    Returns:
        Dict: Dados formatados para visualização
    """
    try:
        # Dados básicos
        resultado = {
            "tipo": tipo_consulta,
            "titulo": "",
            "subtitulo": "",
            "labels": [],
            "datasets": []
        }
        
        if tipo_consulta == "consumo":
            resultado["titulo"] = "Histórico de Consumo"
            resultado["subtitulo"] = "Consumo em kWh por período"
            
            if "consumo_por_mes" in dados:
                # Ordenar os meses
                meses_ordenados = sorted(dados["consumo_por_mes"].keys())
                resultado["labels"] = meses_ordenados
                
                # Dados de consumo
                resultado["datasets"].append({
                    "label": "Consumo (kWh)",
                    "data": [dados["consumo_por_mes"][mes] for mes in meses_ordenados],
                    "backgroundColor": "rgba(54, 162, 235, 0.2)",
                    "borderColor": "rgba(54, 162, 235, 1)",
                    "borderWidth": 1
                })
        
        elif tipo_consulta == "gasto":
            resultado["titulo"] = "Histórico de Gastos"
            resultado["subtitulo"] = "Valor em R$ por período"
            
            if "valores_por_mes" in dados:
                # Ordenar os meses
                meses_ordenados = sorted(dados["valores_por_mes"].keys())
                resultado["labels"] = meses_ordenados
                
                # Dados de valores
                resultado["datasets"].append({
                    "label": "Valor (R$)",
                    "data": [dados["valores_por_mes"][mes] for mes in meses_ordenados],
                    "backgroundColor": "rgba(255, 99, 132, 0.2)",
                    "borderColor": "rgba(255, 99, 132, 1)",
                    "borderWidth": 1
                })
        
        elif tipo_consulta == "comparacao":
            resultado["titulo"] = "Comparação de Períodos"
            resultado["subtitulo"] = dados.get("descricao_comparacao", "")
            
            if "periodos" in dados and "valores" in dados:
                resultado["labels"] = dados["periodos"]
                
                # Dados de comparação
                resultado["datasets"].append({
                    "label": dados.get("label_comparacao", "Comparação"),
                    "data": dados["valores"],
                    "backgroundColor": [
                        "rgba(75, 192, 192, 0.2)", 
                        "rgba(153, 102, 255, 0.2)"
                    ],
                    "borderColor": [
                        "rgba(75, 192, 192, 1)",
                        "rgba(153, 102, 255, 1)"
                    ],
                    "borderWidth": 1
                })
                
                # Adicionar dados de variação
                if "variacao" in dados:
                    resultado["variacao"] = dados["variacao"]
        
        elif tipo_consulta == "previsao":
            resultado["titulo"] = "Previsão de Consumo"
            resultado["subtitulo"] = "Estimativa para os próximos meses"
            
            if "previsao_meses" in dados and "previsao_valores" in dados:
                resultado["labels"] = dados["previsao_meses"]
                
                # Dados de previsão
                resultado["datasets"].append({
                    "label": "Previsão",
                    "data": dados["previsao_valores"],
                    "backgroundColor": "rgba(255, 159, 64, 0.2)",
                    "borderColor": "rgba(255, 159, 64, 1)",
                    "borderWidth": 1,
                    "borderDash": [5, 5]  # Linha tracejada para indicar previsão
                })
                
                # Adicionar margem de erro se disponível
                if "previsao_margem_erro" in dados:
                    resultado["datasets"].append({
                        "label": "Margem de Erro",
                        "data": dados["previsao_margem_erro"],
                        "type": "line",
                        "fill": false,
                        "borderColor": "rgba(255, 159, 64, 0.5)",
                        "borderWidth": 1,
                        "pointRadius": 0
                    })
        
        return resultado
        
    except Exception as e:
        logger.error(f"Erro ao extrair dados visuais: {str(e)}")
        return {
            "tipo": "erro",
            "mensagem": "Não foi possível gerar visualização para estes dados"
        }

def sanitizar_texto(texto: str) -> str:
    """
    Sanitiza um texto removendo possíveis códigos maliciosos.
    
    Args:
        texto: Texto para sanitizar
        
    Returns:
        str: Texto sanitizado
    """
    # Remover possíveis tags HTML
    texto = re.sub(r'<[^>]*>', '', texto)
    
    # Escapar aspas e outros caracteres especiais
    texto = texto.replace('"', '&quot;').replace("'", '&#39;')
    
    return texto

def serializar_para_json(obj: Any) -> Any:
    """
    Serializa objetos complexos para JSON.
    
    Args:
        obj: Objeto para serializar
        
    Returns:
        Any: Objeto serializado
    """
    if isinstance(obj, datetime):
        return obj.isoformat()
    elif hasattr(obj, '__dict__'):
        return obj.__dict__
    else:
        return str(obj)

def converter_mes_referencia(mes_referencia: str) -> datetime:
    """
    Converte string de mês/ano para objeto datetime.
    
    Args:
        mes_referencia: String no formato MM/AAAA
        
    Returns:
        datetime: Objeto datetime representando o primeiro dia do mês
    """
    try:
        partes = mes_referencia.split('/')
        if len(partes) != 2:
            raise ValueError(f"Formato inválido: {mes_referencia}")
        
        mes = int(partes[0])
        ano = int(partes[1])
        
        return datetime(ano, mes, 1)
    except Exception as e:
        logger.error(f"Erro ao converter mês de referência: {str(e)}")
        return datetime.now().replace(day=1)