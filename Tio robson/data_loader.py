"""
data_loader.py - Camada de dados do Dashboard de Segurança Patrimonial.

ARQUITETURA (Fase 2 — SQLite como Fonte Única de Verdade):
  - Todos os dados em runtime vêm do banco SQLite (sp_indicadores.db).
  - O Excel é usado APENAS durante a importação via ETL (database.import_from_excel).
  - Não existem hardcodes de valores, metas ou títulos aqui.
  - mapping_db.py é usado SOMENTE como bootstrap (seed) do banco, não em runtime.
"""

import os
import database as db

MESES = [
    "Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
    "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"
]


def _calc_status(valor, meta_numero, menor_melhor: bool) -> str:
    """Calcula status com base no valor versus meta. Sem hardcodes."""
    if valor is None:
        return "A preencher"
    if meta_numero is None:
        return "Em Atenção"
    if menor_melhor:
        if valor <= meta_numero:
            return "Dentro da meta"
        elif valor <= meta_numero * 1.2:
            return "Em Atenção"
        else:
            return "Acima da meta"
    else:
        if valor >= meta_numero:
            return "Dentro da meta"
        elif valor >= meta_numero * 0.8:
            return "Em Atenção"
        else:
            return "Abaixo da meta"


def _ultimo_valor(hist_ano: dict) -> float | None:
    """Retorna o último valor disponível iterando pelos meses em ordem."""
    for mes in reversed(MESES):
        v = hist_ano.get(mes)
        if v is not None:
            return v
    return None


def get_all_data() -> dict:
    """
    Monta o dicionário completo esperado pelos painéis do dashboard.
    100% lido do SQLite. Sem Excel em runtime.
    """

    # ── 1. Config ─────────────────────────────────────────────────────────
    config = db.get_all_config()

    # ── 2. Indicadores mapeados ────────────────────────────────────────────
    mapeamento = db.get_active()  # Apenas ativos
    codigos = [m["codigo_indicador"] for m in mapeamento]

    # ── 3. Dados históricos (2025 e 2026) em uma única query ──────────────
    historico = db.get_historico_multi(codigos, [2025, 2026])

    # ── 4. Análise crítica ─────────────────────────────────────────────────
    ac_raw_db = db.get_analise_critica()

    # ── 5. Montar lista de indicadores ─────────────────────────────────────
    indicadores = []
    for m in mapeamento:
        cod = m["codigo_indicador"]
        hist = historico.get(cod, {})
        hist_26 = hist.get(2026, {})

        # Últimos dois meses com dado disponível em 2026
        val_jan = hist_26.get("Janeiro")
        val_fev = hist_26.get("Fevereiro")
        val_atual = _ultimo_valor(hist_26)

        status = _calc_status(
            val_atual,
            m.get("meta_numero"),
            bool(m.get("menor_melhor", 1))
        )

        indicadores.append({
            "codigo":           cod,
            "titulo":           m["nome_indicador"],
            "tipo":             m.get("tipo") or "Operacional",
            "periodicidade":    m.get("periodicidade") or "Mensal",
            "unidade":          m.get("unidade") or "",
            "meta":             m.get("meta_texto") or ("Meta a definir" if not m.get("meta_numero") else str(m["meta_numero"])),
            "meta_numero":      m.get("meta_numero"),
            "menor_melhor":     bool(m.get("menor_melhor", 1)),
            "resultado_jan":    val_jan,
            "resultado_fev":    val_fev,
            "status":           status,
            "origem":           m.get("observacoes") or m.get("aba_origem_excel") or "—",
            "aba_origem":       m.get("aba_origem_excel"),
            "campo_origem":     m.get("campo_origem"),
            "modo_comparacao":  m.get("modo_comparacao") or "2025 x 2026",
            # Histórico completo para gráficos
            "hist_2025":        hist.get(2025, {}),
            "hist_2026":        hist.get(2026, {}),
        })

    # ── 6. Comparativos 2025 x 2026 ───────────────────────────────────────
    comparativos = {}
    for m in mapeamento:
        cod = m["codigo_indicador"]
        hist = historico.get(cod, {})
        comparativos[cod] = {
            "nome":         m["nome_indicador"],
            "unidade":      m.get("unidade") or "",
            "dados":        hist,
            "meta_num":     m.get("meta_numero"),
            "menor_melhor": bool(m.get("menor_melhor", 1)),
        }

    # ── 7. sub_raw para gráficos de série temporal ─────────────────────────
    sub_raw = []
    for cod, info in comparativos.items():
        for ano in [2025, 2026]:
            for mes in MESES:
                val = info["dados"].get(ano, {}).get(mes)
                if val is not None:
                    sub_raw.append({
                        "codigo_indicador":  cod,
                        "nome_subindicador": info["nome"],
                        "mes":   mes,
                        "ano":   ano,
                        "valor": val,
                        "meta":  info.get("meta_num"),
                    })

    # ── 8. Pendências (da análise crítica + indicadores sem dados) ─────────
    pendencias = []
    for ac in ac_raw_db:
        cod = ac["codigo_indicador"]
        ind = next((i for i in indicadores if i["codigo"] == cod), None)
        pendencias.append({
            "codigo":    cod,
            "titulo":    ind["titulo"] if ind else cod,
            "nivel":     ac.get("nivel") or "ATENÇÃO",
            "descricao": ac.get("analise") or "",
            "prazo":     ac.get("prazo") or "",
        })

    # Indicadores com status problemático mas sem análise crítica registrada
    codigos_com_ac = {p["codigo"] for p in pendencias}
    for ind in indicadores:
        if ind["status"] in ("A preencher", "Em Atenção") and ind["codigo"] not in codigos_com_ac:
            pendencias.append({
                "codigo":    ind["codigo"],
                "titulo":    ind["titulo"],
                "nivel":     "ATENÇÃO",
                "descricao": f"Status: {ind['status']}. Nenhuma análise crítica registrada.",
                "prazo":     "",
            })

    # ── 9. Stats ───────────────────────────────────────────────────────────
    total       = len(indicadores)
    com_meta    = sum(1 for i in indicadores if "definir" not in str(i.get("meta","")).lower())
    sem_meta    = total - com_meta
    em_atencao  = sum(1 for i in indicadores if i["status"] in ("Em Atenção", "Acima da meta", "Abaixo da meta"))
    a_preencher = sum(1 for i in indicadores if i["status"] == "A preencher")

    stats = {
        "total":              total,
        "com_meta":           com_meta,
        "sem_meta":           sem_meta,
        "em_atencao":         em_atencao,
        "pendentes_processo": 0,
        "a_preencher":        a_preencher,
        "periodo":            config.get("periodo_atual", "—"),
        "responsavel":        config.get("responsavel_geral", "Segurança Patrimonial"),
        "atualizacao":        config.get("data_atualizacao", "—"),
    }

    return {
        "config":       config,
        "indicadores":  indicadores,
        "pendencias":   pendencias,
        "stats":        stats,
        "comparativos": comparativos,
        "sub_raw":      sub_raw,
        "ac_raw":       ac_raw_db,
    }
