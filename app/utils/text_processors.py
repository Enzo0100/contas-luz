import re
import logging
import unicodedata
from typing import Dict, List, Any, Tuple, Optional
from datetime import datetime, timedelta

# Configuração de logging
logger = logging.getLogger("utils.text_processors")

class TextClassifier:
    """
    Classificador de texto para consultas de contas de luz.
    Utiliza regras e expressões regulares para classificar intenções.
    """
    
    TIPOS_CONSULTA = [
        "consumo",       # Consultas sobre consumo em kWh
        "gasto",         # Consultas sobre valores gastos
        "comparacao",    # Consultas comparando períodos
        "previsao",      # Consultas sobre previsões futuras
        "analise",       # Consultas de análise (média, tendências, etc)
        "historico",     # Consultas sobre histórico de contas
        "procedimento",  # Perguntas sobre procedimentos (como economizar, etc)
        "geral"          # Consultas gerais
    ]
    
    def __init__(self):
        """Inicializa o classificador."""
        # Carrega os padrões de cada tipo de consulta
        self.padroes = {
            "consumo": [
                r'(consumo|consumiu|gastou|gasto de energia|kwh|kw/h|quilowatt|quanto.*consum)',
                r'(usar|uso|utiliz|gastos?)\s+(energia|luz|eletricidade)',
                r'(quanto|média).*(energia|luz)',
            ],
            "gasto": [
                r'(gasto|gastei|valor|custo|paguei|conta|fatura|dinheiro|reais|\br\$|quanto .*pag|pagou|pago)',
                r'(quanto|valor|preço).*(conta|fatura|energia|luz)',
                r'(custou|custa|saiu)',
            ],
            "comparacao": [
                r'(compar|diferença|mais que|menos que|aumento|diminuição|variação|percentual|mudança)',
                r'(maior|menor).*(consumo|gasto|valor|conta)',
                r'(antes|depois|anterior)',
            ],
            "previsao": [
                r'(previs|próximo|futur|estim|estimar|projeção|quanto.*(será|vai custar|vou gastar|vai dar|vai ficar))',
                r'(próximo|seguinte).*(mês|mes|bimestre|trimestre|fatura|conta)',
                r'(vai|irá).*(aumentar|diminuir|custar)',
            ],
            "analise": [
                r'(análise|analisar|tendência|padrão|média|regular|normal|usual|tendência|comportamento)',
                r'(média|mediana|total).*(consumo|gasto|energia|luz)',
                r'(máximo|mínimo|maior|menor).*(conta|valor|consumo)',
            ],
            "historico": [
                r'(histórico|antigo|anterior|passado|últimos?|anteriores).*(conta|consumo|gasto|fatura)',
                r'(meses|bimestre|trimestre|semestre|ano).*(anteriores|passados)',
                r'(desde|quando|tempo).*(início|começo)',
            ],
            "procedimento": [
                r'(como|dica|sugestão|reduzir|diminuir|economizar|poupar).*(gasto|consumo|energia|luz|conta)',
                r'(eficien|redução|diminuição).*(energética|consumo|gasto)',
                r'(ajudar?|economia|ajuda).*(conta|fatura|energia|luz)',
            ]
        }
    
    def classificar(self, texto: str) -> Dict[str, float]:
        """
        Classifica um texto de acordo com os tipos de consulta.
        
        Args:
            texto: Texto da consulta
            
        Returns:
            Dict[str, float]: Dicionário com scores para cada tipo de consulta
        """
        # Normalizar o texto
        texto_norm = self._normalizar_texto(texto)
        
        # Inicializar scores
        scores = {tipo: 0.0 for tipo in self.TIPOS_CONSULTA}
        
        # Avaliar cada tipo de consulta
        for tipo, padroes in self.padroes.items():
            for padrao in padroes:
                # Buscar o padrão no texto
                matches = re.findall(padrao, texto_norm, re.IGNORECASE)
                if matches:
                    # Incrementar score com base na quantidade e qualidade das correspondências
                    scores[tipo] += len(matches) * 0.5
        
        # Se nenhum tipo teve score, atribuir ao tipo "geral"
        if all(score == 0 for tipo, score in scores.items()):
            scores["geral"] = 1.0
        
        # Normalizar scores
        total = sum(scores.values())
        if total > 0:
            for tipo in scores:
                scores[tipo] /= total
        
        return scores
    
    def obter_tipo_principal(self, texto: str) -> str:
        """
        Obtém o tipo de consulta principal.
        
        Args:
            texto: Texto da consulta
            
        Returns:
            str: Tipo principal da consulta
        """
        scores = self.classificar(texto)
        return max(scores.items(), key=lambda x: x[1])[0]
    
    def _normalizar_texto(self, texto: str) -> str:
        """
        Normaliza um texto para processamento.
        
        Args:
            texto: Texto para normalizar
            
        Returns:
            str: Texto normalizado
        """
        # Converter para minúsculas
        texto = texto.lower()
        
        # Remover acentos
        texto = unicodedata.normalize('NFKD', texto)
        texto = ''.join([c for c in texto if not unicodedata.combining(c)])
        
        # Remover caracteres especiais, mantendo letras, números e espaços
        texto = re.sub(r'[^a-z0-9\s]', ' ', texto)
        
        # Remover espaços duplicados
        texto = re.sub(r'\s+', ' ', texto).strip()
        
        return texto


class PeriodExtractor:
    """
    Extrator de períodos de tempo a partir de texto em linguagem natural.
    """
    
    MESES = {
        'janeiro': 1, 'fevereiro': 2, 'março': 3, 'abril': 4, 'maio': 5, 'junho': 6,
        'julho': 7, 'agosto': 8, 'setembro': 9, 'outubro': 10, 'novembro': 11, 'dezembro': 12,
        'jan': 1, 'fev': 2, 'mar': 3, 'abr': 4, 'mai': 5, 'jun': 6,
        'jul': 7, 'ago': 8, 'set': 9, 'out': 10, 'nov': 11, 'dez': 12
    }
    
    def __init__(self):
        """Inicializa o extrator de períodos."""
        pass
    
    def extrair_periodo(self, texto: str) -> Tuple[datetime, datetime]:
        """
        Extrai período de datas a partir de texto em linguagem natural.
        
        Args:
            texto: Texto com menção a período
            
        Returns:
            Tuple[datetime, datetime]: Data inicial e final do período
        """
        texto = texto.lower()
        hoje = datetime.now()
        
        # Período padrão (últimos 3 meses)
        data_inicial = hoje.replace(day=1) - timedelta(days=90)
        data_final = hoje
        
        # Verificar menções a "último mês", "mês passado"
        if re.search(r'(último|passado|anterior)\s+(mês|mes)', texto):
            mes_anterior = hoje.replace(day=1) - timedelta(days=1)
            data_inicial = mes_anterior.replace(day=1)
            data_final = mes_anterior.replace(day=1) + self._ultimo_dia_mes(mes_anterior.month, mes_anterior.year)
        
        # Verificar menções a "últimos X meses"
        match = re.search(r'(últimos|ultimos|passados|anteriores)\s+(\d+)\s+(meses|mes)', texto)
        if match:
            num_meses = int(match.group(2))
            data_inicial = (hoje.replace(day=1) - timedelta(days=1)).replace(day=1)
            for _ in range(num_meses - 1):
                data_inicial = (data_inicial - timedelta(days=1)).replace(day=1)
            data_final = hoje
        
        # Verificar menções a "este mês", "mês atual"
        if re.search(r'(este|atual|corrente)\s+(mês|mes)', texto):
            data_inicial = hoje.replace(day=1)
            data_final = hoje
        
        # Verificar menções a "último ano", "ano passado"
        if re.search(r'(último|passado|anterior)\s+ano', texto):
            ano_anterior = hoje.year - 1
            data_inicial = datetime(ano_anterior, 1, 1)
            data_final = datetime(ano_anterior, 12, 31)
        
        # Verificar menções a "este ano", "ano atual"
        if re.search(r'(este|atual|corrente)\s+ano', texto):
            data_inicial = datetime(hoje.year, 1, 1)
            data_final = hoje
        
        # Verificar menções a meses específicos
        for mes_nome, mes_num in self.MESES.items():
            if mes_nome in texto:
                # Procurar menções a anos específicos
                match_ano = re.search(r'\b(20\d{2})\b', texto)
                ano = int(match_ano.group(1)) if match_ano else hoje.year
                
                # Verificar se é um período: "de janeiro a março"
                match_periodo = re.search(fr'de\s+{mes_nome}\s+(?:a|até|ao?)\s+([a-zç]+)', texto)
                if match_periodo:
                    mes_final_nome = match_periodo.group(1)
                    if mes_final_nome in self.MESES:
                        mes_final_num = self.MESES[mes_final_nome]
                        data_inicial = datetime(ano, mes_num, 1)
                        
                        # Se o mês final é menor que o inicial, assume-se que é no ano seguinte
                        ano_final = ano if mes_final_num >= mes_num else ano + 1
                        
                        # Último dia do mês final
                        ultimo_dia = self._ultimo_dia_mes(mes_final_num, ano_final)
                        data_final = datetime(ano_final, mes_final_num, ultimo_dia)
                        break