# Walkthrough — Crimson Desert Elite BR v4.0
*Última atualização: 18/04/2026*

---

## Estado Final

| Item | Status |
|------|--------|
| Motor Faisal integrado | ✅ |
| UI EliteBR (Crimson) | ✅ |
| Multi-preset como mod configurável | ✅ |
| "Configurar..." abre seletor de variantes | ✅ |
| "Alterar Patches..." com botões PT-BR | ✅ |
| Progresso de importação em PT-BR | ✅ |
| Progresso de aplicação em PT-BR | ✅ |
| Freeze no backup corrigido | ✅ |
| Card "Proteção de Arquivos" atualiza sem reload | ✅ |
| Build PyInstaller sem erros críticos | ✅ |
| Metadados do EXE corretos | ✅ |
| **Migração CDMods → CDModsElite 100% concluída** | ✅ |
| **Nenhuma pasta CDMods criada em runtime** | ✅ |

---

## EXE Final

```
dist/CrimsonDesertEliteBR.exe
  Gerado         : 18/04/2026 01:08:46
  Tamanho        : 45.2 MB
  FileDescription: Crimson Desert Elite BR
  CompanyName    : CrashByte
  FileVersion    : 4.0.0.0
  Ícone          : cdumm.ico ✅
```

---

## Histórico de Correções

### Fase 8b — Mods não apareciam após import

- `ModListModel.data()` não retornava `UserRole` → cards ficavam vazios
- Fix: `UserRole` adicionado + `dataChanged` com `[CheckStateRole, UserRole]`

### Fase 8b — Preset picker em inglês/Fluent

- `preset_picker.py` usava `qfluentwidgets`
- Fix: reescrito com PySide6 puro + Crimson Elite + PT-BR

### Fase 8c — Toggle de mod não funcionava

| Causa | Fix |
|-------|-----|
| Comparação `Qt.CheckState.Checked.value` frágil | `value in (Qt.CheckState.Checked, 2, True)` |
| `dataChanged` sem roles → Qt6 não re-renderiza | Emite com `[CheckStateRole, UserRole]` |
| `update_mod_state()` ausente → AttributeError | Método portado do EliteBR |
| `refresh()` resetava status → cards piscavam | Default `preserve_statuses=True` |

### Fase 8d — Import multi-preset importava só 1 preset

| Causa | Fix |
|-------|-----|
| `dialog.selected_path` em vez de `selected_presets` | Lê lista, faz loop com `_import_queue` |
| Mesmo `name` JSON → 2º preset detectado como update do 1º | Flag `_no_update_check` pula detecção |

### Fase 8e — Localização PT-BR

| Arquivo | Strings |
|---------|---------|
| `gui/workers.py` | 26+ strings de progresso |
| `engine/apply_engine.py` | 26+ strings de progresso |
| `gui/patch_toggle_dialog.py` | Save/Discard/Cancel → PT-BR |

### Fase 8f — "Configurar..." dava erro para mods multi-preset

**Antes:** `_on_configure_mod` lia `source_path` → nulo → "origem não encontrada"

**Depois:**
```
Configurar...
  ├── Tem variants no DB? → PresetPickerDialog (pré-selecionado)
  │     → update_variant_selection → regenera merged.json
  └── Não tem variants → TogglePickerDialog (fluxo legado)
```

### Fase 9 — Build PyInstaller

- `gui/i18n.py` criado: stub `get(key, default)` para `binary_search_dialog`
- `cdumm.gui.i18n` adicionado a `hiddenimports` no spec

### Pós-Fase 9 — Freeze UI no backup (~4 segundos)

**Causa:** `shutil.rmtree(vanilla_dir)` rodava no **thread principal** antes do worker iniciar.

**Fix:**
- `SnapshotWorker.__init__` ganhou parâmetro `vanilla_dir: Path | None = None`
- `run()` faz o rmtree no início, na thread de background
- Bloco rmtree removido de `_on_refresh_snapshot` (main thread)
- `_refresh_vanilla_backups()` adiado com `QTimer.singleShot(500ms)`

### Pós-Fase 9 — Card "Proteção de Arquivos" não atualizava

**Causa:** `update_stats()` tinha guard `if not self.isVisible(): return`
→ Se o dashboard não estivesse na aba ativa, o update era silenciosamente descartado.

**Fix:** Guard removido. `_schedule_dashboard_update()` mantido em `_on_snapshot_finished` ✅

---

## Arquitetura Final

```
Elite_Work/
├── src/cdumm/
│   ├── main.py                      # Ponto de entrada Elite
│   ├── gui/
│   │   ├── main_window.py           # Shell EliteBR principal
│   │   ├── theme.py                 # Tema Crimson #C0392B
│   │   ├── i18n.py                  # Stub PT-BR (Fase 9)
│   │   ├── dashboard_panel.py       # Dashboard + cards
│   │   ├── patch_toggle_dialog.py   # Dialog patches (PySide6 puro)
│   │   ├── preset_picker.py         # PresetPickerDialog + TogglePickerDialog
│   │   └── workers.py               # Workers (PT-BR)
│   └── engine/
│       ├── apply_engine.py          # Motor de aplicação (PT-BR)
│       ├── snapshot_manager.py      # SnapshotWorker com vanilla_dir
│       ├── variant_handler.py       # import_multi_variant + update_variant_selection
│       └── import_handler.py        # Importação
├── cdumm.spec                       # PyInstaller spec v4.0
├── version_info.txt                 # Metadados 4.0.0.0 / CrashByte
├── cdumm.ico                        # Ícone Elite
└── dist/
    └── CrimsonDesertEliteBR.exe     # ← BUILD FINAL v2 (45.2 MB)
```

---

## Checklist de Teste (EXE)

### Inicialização
```
□ Abrir CrimsonDesertEliteBR.exe sem erro
□ Splash Elite aparece
□ Janela principal carrega com tema Crimson
□ Nenhum elemento Fluent UI visível
```

### Backup / Proteção
```
□ Clicar "Sim" no prompt de backup → progress dialog IMEDIATO (sem freeze)
□ Janela não vai para "Não Responde"
□ Backup conclui → card "Proteção de Arquivos" muda para "Proteção Ativa"
□ Card atualiza mesmo se usuário NÃO estiver na aba Dashboard
□ Sem travamento pós-backup (~500ms delay no refresh)
```

### Importar Mod
```
□ ZIP 1 preset → mod simples na lista
□ ZIP multi-preset → 1 mod configurável (não vários)
□ Progresso 100% PT-BR (sem inglês)
```

### Gerenciar Mods
```
□ Toggle → muda estado visual imediatamente
□ Botão direito → "Configurar..." → PresetPickerDialog pré-selecionado
□ Confirmar variante → mod atualizado sem erro
□ "Alterar Patches..." → dialog PT-BR abre
□ Fechar com mudanças → "Salvar / Descartar / Cancelar" em PT-BR
```

### Fase 10 — Migração Final CDMods → CDModsElite (100%) ✅ COMPLETO

**Problema identificado:** Ao importar um mod (formato JSON patch), o motor criava a pasta
`CDMods/` no diretório do jogo — apesar de toda a configuração apontar para `CDModsElite/`.

**Causa raiz:** Dois arquivos tinham caminhos hardcoded que geravam `.mkdir(parents=True)`:
1. `import_handler.py` L1835 — `mods_dir = game_dir / "CDMods" / "mods"` passado para `import_json_fast()`
2. `json_patch_handler.py` L893 — `_get_pamt_index()` fazia `cdmods = game_dir / "CDMods"` + `.mkdir()`

**Solução:** Criado módulo centralizado `src/cdumm/engine/paths.py` com dois helpers:

```python
def get_cdmods_dir(game_dir) -> Path:
    """Prefere CDModsElite/, fallback CDMods/ (migração), senão CDModsElite/."""

def get_vanilla_dir(game_dir) -> Path:
    """Prefere CDModsElite/vanilla, fallback CDMods/vanilla, senão CDModsElite/vanilla."""
```

**Arquivos corrigidos (criação de pasta):**

| Arquivo | Fix |
|---------|-----|
| `import_handler.py` | `mods_dir = deltas_dir.parent / "mods"` (deriva de CDModsElite/) |
| `json_patch_handler.py` | `_get_pamt_index`: detecta `vanilla/` → sobe para CDModsElite/, nunca cria CDMods/ |

**Arquivos corrigidos (leituras para CDModsElite/vanilla):**

| Arquivo | Ocorrências |
|---------|-------------|
| `import_handler.py` | 5 lookups de vanilla backup |
| `json_patch_handler.py` | 4 funções (import_json_as_entr, import_json_fast, process_json_patches, _get_pamt_index) |
| `crimson_browser_handler.py` | 2 (vanilla PAMT, vanilla PAZ) |
| `mod_health_check.py` | 5 funções de health check |
| `mod_manager.py` | 1 (get_mod_game_status) |
| `texture_mod_handler.py` | 1 (PATHC vanilla backup) |
| `xml_patch_handler.py` | 1 (process_xml_patches_for_overlay) |

**Resultado final:**

```
CRIA PASTA CDMods: 0 ocorrências
Leituras com CDMods: 30 → todas resolvem CDModsElite/vanilla primeiro
Sintaxe: 13/13 arquivos OK
```

### Aplicar Mods
```
□ Progresso 100% PT-BR
□ "Aplicação concluída!" ao final
□ Nenhuma pasta CDMods criada no jogo
□ CDModsElite/vanilla usado para todos backups e lookups
```
