"""
data_loader.py - Camada de dados do Dashboard de Segurança Patrimonial.

Fonte única: SQLite via database.py.
Excel não é lido em nenhum momento.
Banco pode estar vazio — todos os painéis lidam com listas vazias.
"""

import database as db

MESES = [
    "Janeiro","Fevereiro","Março","Abril","Maio","Junho",
    "Julho","Agosto","Setembro","Outubro","Novembro","Dezembro"
]


OPERADORES = ("<", "<=", "=", ">=", ">")


def _calc_status(valor, meta_operador: str | None, meta_numero) -> str:
    """Regra de status clara e exaustiva.

    A preencher  → não há valor atual
    Sem meta     → há valor mas não há meta definida
    Dentro da meta → valor avalia True com operador + meta_numero
    Em Atenção  → há meta, há valor, mas não atende
    """
    if valor is None:
        return "A preencher"
    if not meta_operador or meta_numero is None:
        return "Sem meta"
    try:
        ok = (
            (meta_operador == "<"  and valor <  meta_numero) or
            (meta_operador == "<=" and valor <= meta_numero) or
            (meta_operador == "="  and valor == meta_numero) or
            (meta_operador == ">=" and valor >= meta_numero) or
            (meta_operador == ">"  and valor >  meta_numero)
        )
    except TypeError:
        return "Em Atenção"
    return "Dentro da meta" if ok else "Em Atenção"


def _ultimo_valor(hist_ano: dict):
    for mes in reversed(MESES):
        v = hist_ano.get(mes)
        if v is not None:
            return v
    return None


def get_all_data() -> dict:
    """Monta o dicionário consumido por todos os painéis. Seguro com banco vazio."""

    config    = db.get_all_config()
    mapeamento = db.get_indicadores_ativos()

    indicadores  = []
    comparativos = {}
    sub_raw      = []

    for m in mapeamento:
        cod     = m["codigo_indicador"]
        hist    = db.get_historico_indicador(cod, [2025, 2026])
        hist_26 = hist.get(2026, {})
        hist_25 = hist.get(2025, {})

        val_jan   = hist_26.get("Janeiro")
        val_fev   = hist_26.get("Fevereiro")
        val_atual = _ultimo_valor(hist_26)

        meta_op  = m.get("meta_operador")
        meta_num = m.get("meta_numero")
        status = _calc_status(val_atual, meta_op, meta_num)

        # Texto exibível da meta (gerado automaticamente se vazio)
        if meta_op and meta_num is not None:
            meta_exib = f"{meta_op} {meta_num}"
        else:
            meta_exib = "Sem meta"

        indicadores.append({
            "codigo":        cod,
            "titulo":        m["nome_indicador"],
            "tipo":          m.get("tipo") or "Operacional",
            "periodicidade": m.get("periodicidade") or "Mensal",
            "unidade":       m.get("unidade") or "",
            "meta":          meta_exib,
            "meta_operador": meta_op,
            "meta_numero":   meta_num,
            "resultado_jan": val_jan,
            "resultado_fev": val_fev,
            "status":        status,
            "origem":        m.get("observacoes") or "—",
            "hist_2025":     hist_25,
            "hist_2026":     hist_26,
        })

        comparativos[cod] = {
            "nome":         m["nome_indicador"],
            "unidade":      m.get("unidade") or "",
            "dados":        hist,
            "meta_operador": m.get("meta_operador"),
            "meta_num":     m.get("meta_numero"),
        }

    # sub_raw para gráficos — lido dos subindicadores reais
    for sub in db.get_all_subindicadores():
        if not sub.get("ativo"):
            continue
        for ano in [2025, 2026]:
            hist_s = db.get_historico_subindicador(sub["id"], [ano])
            for mes in MESES:
                val = hist_s.get(ano, {}).get(mes)
                if val is not None:
                    sub_raw.append({
                        "codigo_indicador":  sub["codigo_indicador"],
                        "subindicador_id":   sub["id"],
                        "nome_subindicador": sub["nome_subindicador"],
                        "mes":   mes,
                        "ano":   ano,
                        "valor": val,
                        "meta":  None,
                    })

    ac_raw     = db.get_analise_critica()
    pendencias = []
    codigos_ac = {a["codigo_indicador"] for a in ac_raw}

    for ac in ac_raw:
        cod = ac["codigo_indicador"]
        ind = next((i for i in indicadores if i["codigo"] == cod), None)
        pendencias.append({
            "codigo":      cod,
            "titulo":      ind["titulo"] if ind else cod,
            "nivel":       ac.get("nivel") or "ATENÇÃO",
            "descricao":   ac.get("analise") or "",
            "causa":       ac.get("causa") or "",
            "acao":        ac.get("acao") or "",
            "responsavel": ac.get("responsavel") or "",
            "prazo":       ac.get("prazo") or "",
        })

    for ind in indicadores:
        if ind["status"] in ("A preencher","Em Atenção") and ind["codigo"] not in codigos_ac:
            pendencias.append({
                "codigo":      ind["codigo"],
                "titulo":      ind["titulo"],
                "nivel":       "ATENÇÃO",
                "descricao":   f"Status: {ind['status']}. Sem análise crítica registrada.",
                "causa": "", "acao": "", "responsavel": "", "prazo": "",
            })

    # ── Stats coerentes com nova lógica de status ─────────────────────────────
    total       = len(indicadores)
    com_meta    = sum(1 for i in indicadores if i["meta_operador"] and i["meta_numero"] is not None)
    atingidas   = sum(1 for i in indicadores if i["status"] == "Dentro da meta")
    em_atencao  = sum(1 for i in indicadores if i["status"] == "Em Atenção")
    sem_meta    = sum(1 for i in indicadores if i["status"] == "Sem meta")
    a_preencher = sum(1 for i in indicadores if i["status"] == "A preencher")

    stats = {
        "total":              total,
        "com_meta":           com_meta,
        "sem_meta":           sem_meta,
        "atingidas":          atingidas,
        "em_atencao":         em_atencao,
        "a_preencher":        a_preencher,
        "periodo":            config.get("periodo_atual") or "—",
        "responsavel":        config.get("responsavel") or "—",
        "atualizacao":        config.get("data_atualizacao") or "—",
    }

    return {
        "config":       config,
        "indicadores":  indicadores,
        "pendencias":   pendencias,
        "stats":        stats,
        "comparativos": comparativos,
        "sub_raw":      sub_raw,
        "ac_raw":       ac_raw,
    }
