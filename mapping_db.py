"""
mapping_db.py - Base de mapeamento interno dos indicadores.
Define a relação entre cada indicador e sua fonte real de dados.
Substitui os chutes hardcoded de status/vínculo.
"""

# Status possíveis de mapeamento
STATUS_MAPEADO           = "Mapeado"
STATUS_PENDENTE_PROCESSO = "Pendente de processo"
STATUS_PENDENTE_CONTROLE = "Pendente de controle"
STATUS_SEM_VINCULO       = "Sem vínculo"

# Mapeamento real, revisado com base na leitura dos arquivos operacionais
# usa_dados_operacionais: True = lê da planilha INDICADORES CONTROLE GERAL SEGURANÇA - 2026.xlsx
# aba_origem_excel: nome da aba no arquivo operacional (None se não existir)
# campo_origem: nome do campo/coluna que representa o resultado
# resultado_representa: o que o valor numérico significa
# subindicadores_existem: False até que sejam implementados de verdade
# status_mapeamento: status atual do vínculo
# observacoes: notas para orientar o responsável

MAPEAMENTO_INDICADORES = [
    {
        "codigo_indicador":       "SP.IND.001",
        "nome_indicador":         "Incidência de Intercorrências de Segurança Patrimonial",
        "usa_dados_operacionais": True,
        "aba_origem_excel":       "INTERCORRENCIAS SEG",
        "campo_origem":           "INTERCORRÊNCIAS (coluna total)",
        "resultado_representa":   "Valor total mensal",
        "subindicadores_existem": False,
        "subindicadores_status":  "A definir",
        "status_mapeamento":      STATUS_MAPEADO,
        "observacoes":            "Leitura da coluna 'INTERCORRÊNCIAS' mês a mês. Jan=42, Fev=38 (2026).",
    },
    {
        "codigo_indicador":       "SP.IND.002",
        "nome_indicador":         "Índice de Conformidade de Segurança Patrimonial",
        "usa_dados_operacionais": False,
        "aba_origem_excel":       None,
        "campo_origem":           None,
        "resultado_representa":   "% de conformidade",
        "subindicadores_existem": False,
        "subindicadores_status":  "Não implementado",
        "status_mapeamento":      STATUS_PENDENTE_PROCESSO,
        "observacoes":            "Necessita implantação de processo formal + checklist de ronda. Sem base de dados disponível.",
    },
    {
        "codigo_indicador":       "SP.IND.003",
        "nome_indicador":         "Atendimento às Solicitações de Óbito",
        "usa_dados_operacionais": True,
        "aba_origem_excel":       "MORGUE",
        "campo_origem":           "Óbitos recolhidos (coluna do ano)",
        "resultado_representa":   "Quantidade de óbitos recolhidos mensalmente",
        "subindicadores_existem": False,
        "subindicadores_status":  "A definir",
        "status_mapeamento":      STATUS_MAPEADO,
        "observacoes":            "Jan=137, Fev=129 (2026). Meta ainda não definida.",
    },
    {
        "codigo_indicador":       "SP.IND.004",
        "nome_indicador":         "Acesso de Pessoas à Instituição",
        "usa_dados_operacionais": True,
        "aba_origem_excel":       "VISITAS",
        "campo_origem":           "Visitantes + Acompanhantes (soma)",
        "resultado_representa":   "Total de acessos mensais",
        "subindicadores_existem": False,
        "subindicadores_status":  "A definir — Visitantes e Acompanhantes são candidatos",
        "status_mapeamento":      STATUS_MAPEADO,
        "observacoes":            "Soma de visitantes + acompanhantes. Jan=19594, Fev=20495 (2026).",
    },
    {
        "codigo_indicador":       "SP.IND.005",
        "nome_indicador":         "Acesso de Veículos",
        "usa_dados_operacionais": True,
        "aba_origem_excel":       "PATIO",
        "campo_origem":           "Total A+B (Ambulâncias + Outros)",
        "resultado_representa":   "Total de veículos no mês",
        "subindicadores_existem": False,
        "subindicadores_status":  "A definir — Ambulâncias e Outros veículos são candidatos",
        "status_mapeamento":      STATUS_MAPEADO,
        "observacoes":            "Jan=2049, Fev=1647 (2026). Inclui Pátio Nutrição separado.",
    },
    {
        "codigo_indicador":       "SP.IND.006",
        "nome_indicador":         "Evasão de Pacientes",
        "usa_dados_operacionais": True,
        "aba_origem_excel":       "EVASÃO",
        "campo_origem":           "Evasão (coluna 2026)",
        "resultado_representa":   "Número de evasões mensais",
        "subindicadores_existem": False,
        "subindicadores_status":  "A definir",
        "status_mapeamento":      STATUS_MAPEADO,
        "observacoes":            "Meta: ≤ 3. Jan=3, Fev=1 (2026). Dentro da meta.",
    },
    {
        "codigo_indicador":       "SP.IND.007",
        "nome_indicador":         "Apreensões",
        "usa_dados_operacionais": True,
        "aba_origem_excel":       "APREENSÕES",
        "campo_origem":           "Armas/Objetos + Tabaco/Entorpecentes (soma)",
        "resultado_representa":   "Total de apreensões no mês",
        "subindicadores_existem": False,
        "subindicadores_status":  "A definir — Armas e Entorpecentes são candidatos a subindicadores",
        "status_mapeamento":      STATUS_MAPEADO,
        "observacoes":            "Jan=20, Fev=16 (2026). Meta não definida.",
    },
    {
        "codigo_indicador":       "SP.IND.008",
        "nome_indicador":         "Pacientes Monitorados por Dispositivos Tornozelados",
        "usa_dados_operacionais": False,
        "aba_origem_excel":       None,
        "campo_origem":           None,
        "resultado_representa":   "% de monitorados",
        "subindicadores_existem": False,
        "subindicadores_status":  "Não implementado",
        "status_mapeamento":      STATUS_PENDENTE_CONTROLE,
        "observacoes":            "Necessita criação de controle formal com registro periódico. Fonte externa (unidade).",
    },
]

# Índice de acesso rápido por código
MAPEAMENTO_INDEX = {m["codigo_indicador"]: m for m in MAPEAMENTO_INDICADORES}


def get_mapeamento(codigo: str) -> dict:
    """Retorna o mapeamento de um indicador pelo código. Retorna dict vazio se não encontrado."""
    return MAPEAMENTO_INDEX.get(codigo, {})


def get_stats_mapeamento() -> dict:
    """Retorna estatísticas do mapeamento para os KPI cards da tela Base de Dados."""
    total      = len(MAPEAMENTO_INDICADORES)
    mapeados   = sum(1 for m in MAPEAMENTO_INDICADORES if m["status_mapeamento"] == STATUS_MAPEADO)
    sem_vinculo= sum(1 for m in MAPEAMENTO_INDICADORES if m["status_mapeamento"] == STATUS_SEM_VINCULO)
    pendentes  = sum(1 for m in MAPEAMENTO_INDICADORES
                     if m["status_mapeamento"] in (STATUS_PENDENTE_PROCESSO, STATUS_PENDENTE_CONTROLE))

    return {
        "total":            total,
        "mapeados":         mapeados,
        "pct_mapeados":     round(mapeados / total * 100) if total else 0,
        "sem_vinculo":      sem_vinculo,
        "pct_sem_vinculo":  round(sem_vinculo / total * 100) if total else 0,
        "pendentes":        pendentes,
        "pct_pendentes":    round(pendentes / total * 100) if total else 0,
        "linhas_banco":     total,
    }
