"""
data_loader.py - Camada de dados do Dashboard de Segurança Patrimonial.

Arquitetura (SQLite-First):
  - Fonte única: SQLite via database.py
  - Excel: apenas importação opcional, nunca em runtime
  - Modelo: indicadores → subindicadores → dados_historicos
"""

import database as db

MESES = [
    "Janeiro","Fevereiro","Março","Abril","Maio","Junho",
    "Julho","Agosto","Setembro","Outubro","Novembro","Dezembro"
]


def _calc_status(valor, meta_numero, menor_melhor: bool) -> str:
    if valor is None:
        return "A preencher"
    if meta_numero is None:
        return "Em Atenção"
    if menor_melhor:
        if valor <= meta_numero:           return "Dentro da meta"
        elif valor <= meta_numero * 1.2:   return "Em Atenção"
        else:                              return "Acima da meta"
    else:
        if valor >= meta_numero:           return "Dentro da meta"
        elif valor >= meta_numero * 0.8:   return "Em Atenção"
        else:                              return "Abaixo da meta"


def _ultimo_valor(hist_ano: dict):
    for mes in reversed(MESES):
        v = hist_ano.get(mes)
        if v is not None:
            return v
    return None


def get_all_data() -> dict:
    """
    Monta o dicionário completo consumido por todos os painéis.
    100% lido do SQLite. Zero Excel em runtime.
    """
    # ── Config ────────────────────────────────────────────────────────────
    config = db.get_all_config()

    # ── Indicadores ativos ─────────────────────────────────────────────────
    mapeamento = db.get_indicadores_ativos()
    codigos    = [m["codigo_indicador"] for m in mapeamento]

    # ── Histórico agregado 2025/2026 ───────────────────────────────────────
    # Para cada indicador: soma dos subindicadores
    historico = {}  # {codigo: {ano: {mes: valor}}}
    for cod in codigos:
        historico[cod] = db.get_historico_indicador(cod, [2025, 2026])

    # ── Análise crítica ────────────────────────────────────────────────────
    ac_raw_db = db.get_analise_critica()

    # ── Lista de indicadores ───────────────────────────────────────────────
    indicadores = []
    for m in mapeamento:
        cod     = m["codigo_indicador"]
        hist    = historico.get(cod, {})
        hist_26 = hist.get(2026, {})

        val_jan  = hist_26.get("Janeiro")
        val_fev  = hist_26.get("Fevereiro")
        val_atual = _ultimo_valor(hist_26)

        status = _calc_status(
            val_atual,
            m.get("meta_numero"),
            bool(m.get("menor_melhor", 1))
        )

        indicadores.append({
            "codigo":         cod,
            "titulo":         m["nome_indicador"],
            "tipo":           m.get("tipo") or "Operacional",
            "periodicidade":  m.get("periodicidade") or "Mensal",
            "unidade":        m.get("unidade") or "",
            "meta":           m.get("meta_texto") or ("Meta a definir" if not m.get("meta_numero") else str(m["meta_numero"])),
            "meta_numero":    m.get("meta_numero"),
            "menor_melhor":   bool(m.get("menor_melhor", 1)),
            "resultado_jan":  val_jan,
            "resultado_fev":  val_fev,
            "status":         status,
            "origem":         m.get("observacoes") or "—",
            "hist_2025":      hist.get(2025, {}),
            "hist_2026":      hist.get(2026, {}),
        })

    # ── Comparativos 2025 x 2026 ───────────────────────────────────────────
    comparativos = {}
    for m in mapeamento:
        cod = m["codigo_indicador"]
        comparativos[cod] = {
            "nome":         m["nome_indicador"],
            "unidade":      m.get("unidade") or "",
            "dados":        historico.get(cod, {}),
            "meta_num":     m.get("meta_numero"),
            "menor_melhor": bool(m.get("menor_melhor", 1)),
        }

    # ── sub_raw para gráficos de série temporal ────────────────────────────
    # Agora gerado a partir dos subindicadores reais
    sub_raw = []
    all_subs = db.get_all_subindicadores()
    for sub in all_subs:
        if not sub.get("ativo"):
            continue
        hist_sub = db.get_historico_subindicador(sub["id"], [2025, 2026])
        for ano in [2025, 2026]:
            for mes in MESES:
                val = hist_sub.get(ano, {}).get(mes)
                if val is not None:
                    sub_raw.append({
                        "codigo_indicador":  sub["codigo_indicador"],
                        "subindicador_id":   sub["id"],
                        "nome_subindicador": sub["nome_subindicador"],
                        "mes":   mes,
                        "ano":   ano,
                        "valor": val,
                        "meta":  sub.get("meta_numero"),
                    })

    # ── Pendências ─────────────────────────────────────────────────────────
    pendencias = []
    for ac in ac_raw_db:
        cod = ac["codigo_indicador"]
        ind = next((i for i in indicadores if i["codigo"] == cod), None)
        pendencias.append({
            "codigo":    cod,
            "titulo":    ind["titulo"] if ind else cod,
            "nivel":     ac.get("nivel") or "ATENÇÃO",
            "descricao": ac.get("analise") or "",
            "causa":     ac.get("causa") or "",
            "acao":      ac.get("acao") or "",
            "responsavel": ac.get("responsavel") or "",
            "prazo":     ac.get("prazo") or "",
        })

    # Indicadores problemáticos sem análise crítica registrada
    codigos_com_ac = {p["codigo"] for p in pendencias}
    for ind in indicadores:
        if ind["status"] in ("A preencher", "Em Atenção") and ind["codigo"] not in codigos_com_ac:
            pendencias.append({
                "codigo":    ind["codigo"],
                "titulo":    ind["titulo"],
                "nivel":     "ATENÇÃO",
                "descricao": f"Status: {ind['status']}. Sem análise crítica registrada.",
                "causa": "", "acao": "", "responsavel": "", "prazo": "",
            })

    # ── Stats ──────────────────────────────────────────────────────────────
    total       = len(indicadores)
    com_meta    = sum(1 for i in indicadores if "definir" not in str(i.get("meta","")).lower())
    em_atencao  = sum(1 for i in indicadores if i["status"] in ("Em Atenção","Acima da meta","Abaixo da meta"))
    a_preencher = sum(1 for i in indicadores if i["status"] == "A preencher")

    stats = {
        "total":              total,
        "com_meta":           com_meta,
        "sem_meta":           total - com_meta,
        "em_atencao":         em_atencao,
        "pendentes_processo": 0,
        "a_preencher":        a_preencher,
        "periodo":            config.get("periodo_atual", "—"),
        "responsavel":        config.get("responsavel", config.get("responsavel_geral", "—")),
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
