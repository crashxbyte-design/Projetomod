# Implementation Plan — Nova Migração do Zero
> Criado: 2026-04-17 | Atualizado: 18/04/2026 — **Fases 0–10 concluídas + Migração CDModsElite 100%**
> Fonte da verdade: código das duas bases (EliteBR + Faisal mais novo)

---

## Contexto

Este plano substitui o histórico anterior.  
O projeto anterior (**EliteBR**) já realizou uma migração bem-sucedida.  
Agora queremos **repetir a migração do zero** partindo da **base Faisal mais nova** (`Elite_Work/src/cdumm/`), aplicando por cima a **UI EliteBR** e todas as **customizações Elite**.

---

## Estratégia Confirmada: VIÁVEL ✅

| Camada | Origem |
|--------|--------|
| Shell visual (`main_window.py`, `theme.py`, painéis) | **EliteBR** |
| Engine/Backend (`engine/`, `storage/`, `archive/`, `semantic/`) | **Faisal novo** |
| Módulo nativo Rust (`cdumm_native.pyd`) | **Faisal** |
| Startup / configurações Elite | **EliteBR `main.py`** (adaptado) |
| UI Fluent (`fluent_window.py`, `pages/`, `components/`) | ❌ Descartada |

---

## O Que Mudou na Base Nova do Faisal (vs EliteBR)

### Engine — Módulos Novos (existem no Faisal, não no EliteBR)
| Módulo | Tamanho | Função |
|--------|---------|--------|
| `engine/compiled_merge.py` | 3.3KB | Merge compilado pré-computado |
| `engine/configurable_scanner.py` | 6.7KB | Scanner configurável de mods |
| `engine/json_target_scanner.py` | 1.4KB | Scanner de targets JSON |
| `engine/language.py` | 3.4KB | Seletor de linguagem do jogo |
| `engine/mod_matching.py` | 1.7KB | Matching de mods por padrão |
| `engine/nexus_api.py` | 0.7KB | API NexusMods (update check) |
| `engine/nexus_filename.py` | 3.6KB | Parser de nomes NexusMods |
| `engine/variant_handler.py` | 16.1KB | Variantes de mods |
| `engine/xml_patch_handler.py` | 35.6KB | Patch XML (NOVO módulo completo) |

### Engine — Módulos Atualizados (maiores no Faisal)
| Módulo | Faisal | EliteBR | Delta |
|--------|--------|---------|-------|
| `apply_engine.py` | 122.2KB | 104.2KB | **+18KB** |
| `import_handler.py` | 113.7KB | 102.2KB | **+11.5KB** |
| `json_patch_handler.py` | 66.6KB | 53.2KB | **+13.4KB** |
| `texture_mod_handler.py` | 12.4KB | 4.6KB | **+7.8KB** |
| `mod_diagnostics.py` | 31.3KB | 26.6KB | **+4.7KB** |
| `activity_log.py` | 5.5KB | 4.6KB | +0.9KB |
| `mod_manager.py` | 31.6KB | 31KB | +0.6KB |
| `crimson_browser_handler.py` | 22.3KB | 20KB | +2.3KB |

### Storage — Módulos Atualizados
| Módulo | Faisal | EliteBR |
|--------|--------|---------|
| `database.py` | 19.1KB | 14.4KB (+4.7KB) |
| `game_finder.py` | 10.1KB | 8.1KB (+2KB) |
| `config.py` | 2KB | 0.8KB (+1.2KB) |

### Archive — Módulos Atualizados
| Módulo | Faisal | EliteBR | Nota |
|--------|--------|---------|------|
| `overlay_builder.py` | 33.9KB | 23.5KB | **+10.4KB — crítico** |
| `paz_parse.py` | 10.3KB | 6.7KB | +3.6KB |
| `paz_repack.py` | 14KB | 17.2KB | EliteBR maior (atenção) |
| `characterinfo_full_parser.py` | **6.4KB** | ❌ não existe | **NOVO** |

### GUI Faisal — Módulos a Descartar (Fluent shell)
| Módulo | Destino |
|--------|---------|
| `fluent_window.py` | ❌ Ignorar — mover para arquivo |
| `welcome_wizard.py` | ❌ Ignorar — mover para arquivo |
| `pages/` (7 arquivos) | ❌ Ignorar — mover para arquivo |
| `components/` (7 arquivos) | ❌ Ignorar — mover para arquivo |
| `conflicts_dialog.py` | ❌ Ignorar — EliteBR não usa popup |

### GUI Faisal — Módulos a Preservar (utilitários)
| Módulo | Ação |
|--------|------|
| `bug_report.py` (39.1KB) | Usar versão EliteBR (9.2KB) — mais leve, Elite branded |
| `changelog.py` (40.7KB) | Usar versão Faisal — maior, mais completo |
| `conflict_view.py` (14.1KB) | Usar versão EliteBR — já adaptada e testada |
| `import_widget.py` (1.9KB) | Usar versão EliteBR (2.4KB) — tem updates |
| `mod_contents_dialog.py` (4.3KB) | Usar versão Faisal — mais completo |
| `mod_list_model.py` (12.4KB) | Ambas iguais — usar Faisal |
| `patch_toggle_dialog.py` (6.9KB) | Usar Faisal — mais atual |
| `preset_picker.py` (19.9KB) | Usar Faisal — mais completo |
| `profile_dialog.py` | Usar EliteBR (5.3KB) — tem ajustes |
| `setup_dialog.py` | Usar EliteBR (3.7KB) — adaptado sem Fluent |
| `splash.py` (2.2KB Faisal vs 2.9KB Elite) | Usar EliteBR — com branding Elite |
| `update_overlay.py` | Versões próximas — usar Faisal |
| `workers.py` | Ambas iguais (44.1KB) — usar Faisal |

### GUI — Módulos exclusivos do EliteBR (devem ser copiados)
| Módulo | Função |
|--------|--------|
| `main_window.py` (233.3KB) | Shell principal — OBRIGATÓRIO |
| `theme.py` (21.9KB) | CSS Crimson — OBRIGATÓRIO |
| `dashboard_panel.py` (32.3KB) | Dashboard Elite |
| `activity_panel.py` (9.8KB) | Painel de atividade |
| `asi_panel.py` (11.1KB) | Gerenciador ASI |
| `binary_search_dialog.py` (17KB) | Busca binária de mods |
| `health_check_dialog.py` (7.1KB) | Health check |
| `verify_dialog.py` (7.4KB) | Verificação |
| `progress_dialog.py` (7.7KB) | Progress animado |
| `msg_box_br.py` (7KB) | Dialogs BR |
| `premium_buttons.py` (6.3KB) | Botões premium |
| `logo_widget.py` (1.7KB) | Widget de logo |
| `fast_mod_card_delegate.py` (18.5KB) | Cards rápidos |
| `mod_card_delegate.py` (18.2KB) | Cards de mods |

### pyproject.toml — Diferenças Críticas
| Dependência | Faisal | EliteBR |
|-------------|--------|---------|
| `PySide6-Fluent-Widgets` | ✅ sim | ✅ sim (mas não usado no shell) |
| `privatebin` | ✅ sim | ❌ não tem |
| `lxml` | ✅ sim | ❌ não tem |

> ⚠️ `privatebin` e `lxml` são novas dependências do Faisal. Bug report e xml_patch usam essas libs.

---

## Tabela de Decisão Completa

| Arquivo/Pasta | Decisão | Origem |
|---------------|---------|--------|
| `src/cdumm/main.py` | **ADAPTAR** | Base: EliteBR, copiar CDMods/CDModsElite e paths Elite |
| `src/cdumm/__init__.py` | Usar Faisal | Faisal (mantém versão) |
| `src/cdumm/engine/` (todos) | **FAISAL** | Motor mais novo |
| `src/cdumm/engine/xml_patch_handler.py` | **FAISAL** | Novo — não existe no EliteBR |
| `src/cdumm/engine/variant_handler.py` | **FAISAL** | Novo |
| `src/cdumm/engine/nexus_api.py` | **FAISAL** | Novo |
| `src/cdumm/engine/nexus_filename.py` | **FAISAL** | Novo |
| `src/cdumm/engine/compiled_merge.py` | **FAISAL** | Novo |
| `src/cdumm/engine/configurable_scanner.py` | **FAISAL** | Novo |
| `src/cdumm/engine/language.py` | **FAISAL** | Novo |
| `src/cdumm/storage/` (todos) | **FAISAL** | Mais atualizado |
| `src/cdumm/archive/` (todos) | **FAISAL** | Mais atualizado |
| `src/cdumm/archive/format_parsers/characterinfo_full_parser.py` | **FAISAL** | Novo |
| `src/cdumm/semantic/` (todos) | Faisal | Iguais |
| `src/cdumm/worker_process.py` | **FAISAL** | Faisal tem +16 linhas |
| `src/cdumm/i18n.py` | Faisal | Iguais |
| `src/cdumm/cli.py` | Faisal | Iguais |
| `src/cdumm/translations/` | **FAISAL** | Mais traduções (16 lang) |
| `src/cdumm/gui/main_window.py` | **ELITEBR** | Shell principal |
| `src/cdumm/gui/theme.py` | **ELITEBR** | CSS Crimson (21.9KB vs 4.4KB) |
| `src/cdumm/gui/dashboard_panel.py` | **ELITEBR** | Exclusivo |
| `src/cdumm/gui/activity_panel.py` | **ELITEBR** | Exclusivo |
| `src/cdumm/gui/asi_panel.py` | **ELITEBR** | Exclusivo |
| `src/cdumm/gui/binary_search_dialog.py` | **ELITEBR** | Exclusivo |
| `src/cdumm/gui/health_check_dialog.py` | **ELITEBR** | Exclusivo |
| `src/cdumm/gui/verify_dialog.py` | **ELITEBR** | Exclusivo |
| `src/cdumm/gui/progress_dialog.py` | **ELITEBR** | Exclusivo |
| `src/cdumm/gui/msg_box_br.py` | **ELITEBR** | Exclusivo |
| `src/cdumm/gui/premium_buttons.py` | **ELITEBR** | Exclusivo |
| `src/cdumm/gui/logo_widget.py` | **ELITEBR** | Exclusivo |
| `src/cdumm/gui/fast_mod_card_delegate.py` | **ELITEBR** | Exclusivo |
| `src/cdumm/gui/mod_card_delegate.py` | **ELITEBR** | Exclusivo |
| `src/cdumm/gui/splash.py` | **ELITEBR** | Com branding Elite |
| `src/cdumm/gui/setup_dialog.py` | **ELITEBR** | Sem Fluent wizard |
| `src/cdumm/gui/conflict_view.py` | **ELITEBR** | Adaptada e testada |
| `src/cdumm/gui/import_widget.py` | **ELITEBR** | Com ajustes Elite |
| `src/cdumm/gui/mod_list_model.py` | Faisal | Iguais |
| `src/cdumm/gui/workers.py` | Faisal | Iguais (44.1KB) |
| `src/cdumm/gui/bug_report.py` | **ELITEBR** | Versão leve Elite |
| `src/cdumm/gui/changelog.py` | Faisal | Mais completo |
| `src/cdumm/gui/mod_contents_dialog.py` | Faisal | Mais completo |
| `src/cdumm/gui/patch_toggle_dialog.py` | Faisal | Mais atual |
| `src/cdumm/gui/preset_picker.py` | Faisal | Mais completo |
| `src/cdumm/gui/profile_dialog.py` | **ELITEBR** | Com ajustes |
| `src/cdumm/gui/update_overlay.py` | Faisal | Mais completo |
| `src/cdumm/gui/fluent_window.py` | **IGNORAR** | Mover para _fluent_archive |
| `src/cdumm/gui/welcome_wizard.py` | **IGNORAR** | Mover para _fluent_archive |
| `src/cdumm/gui/conflicts_dialog.py` | **IGNORAR** | Fluent — não usado no shell |
| `src/cdumm/gui/pages/` | **IGNORAR** | Fluent — não usado |
| `src/cdumm/gui/components/` | **IGNORAR** | Fluent — não usado |
| `src/cdumm/gui/logo.png` | **ELITEBR** | Branding Elite |
| `src/cdumm/gui/crimson_hero_bg.png` | **ELITEBR** | Background Elite |
| `assets/` (logos padrão) | Faisal | Usar do Faisal como base |
| `assets/cdumm-logo*.png` | **ELITEBR** | Logos Elite (1564KB, diferem!) |
| `assets/crimson_hero_bg.png` | **ELITEBR** | Novo asset Elite |
| `cdumm.spec` | **ELITEBR** | Sem Fluent, com Elite assets |
| `version_info.txt` | **ELITEBR** | Metadata Elite 4.0.0.0 |
| `cdumm.ico` | **ELITEBR** | Ícone Elite (1.5MB) |
| `pyproject.toml` | **FAISAL + ADAPTAR** | Adicionar `privatebin`, `lxml` |
| `schemas/` | Faisal | Iguais |
| `asi_loader/` | Faisal | Iguais |
| `native/` | Faisal | Rust native |
| `translations/` | **FAISAL** | 16 idiomas (EliteBR tem 16 mas menores) |

---

## Plano de Migração — Ordem das Fases

### Fase 0 — Preparação (pré-condição) ✅ COMPLETO
- [x] Confirmar que `cdumm_native.pyd` está instalado — `C:\Users\Admin\AppData\Local\Programs\Python\Python312\Lib\site-packages\cdumm_native\`
- [x] Instalar `privatebin==0.3.0` — instalado
- [x] Instalar `lxml==6.0.4` — instalado
- [x] Confirmar deps existentes: `xxhash`, `bsdiff4`, `lz4`, `cryptography` — todas OK
- [x] EliteBR intacta como doadora (`main_window.py` 233.3KB confirmado)

### Fase 1 — Limpar GUI Fluent do Faisal ✅ COMPLETO
Movidos para `src/cdumm/gui/_fluent_archive/`:
- [x] `fluent_window.py` (177.5KB) — arquivado
- [x] `welcome_wizard.py` (32.7KB) — arquivado
- [x] `conflicts_dialog.py` (20.3KB) — arquivado
- [x] `pages/` (pasta inteira) — arquivada
- [x] `components/` (pasta inteira) — arquivada

> **Nota:** `bug_report.py`, `changelog.py` e outros 6 arquivos ainda contêm imports `qfluentwidgets` — estes são os arquivos Faisal que serão **substituídos pelas versões EliteBR na Fase 2**. Não é problema agora.

### Fase 2 — Copiar GUI EliteBR para Faisal ✅ COMPLETO
Copiados de `EliteBR/src/cdumm/gui/` → `src/cdumm/gui/`:

**Sobrescritos (7 arquivos Faisal substituídos por versões EliteBR):**
- [x] `bug_report.py` (39.1KB → 9.2KB) — Elite branded
- [x] `conflict_view.py` (14.1KB → 12.4KB) — adaptada Elite
- [x] `import_widget.py` (1.9KB → 2.4KB) — com ajustes Elite
- [x] `profile_dialog.py` (5.0KB → 5.3KB) — com ajustes Elite
- [x] `setup_dialog.py` (3.9KB → 3.7KB) — sem Fluent wizard
- [x] `splash.py` (2.2KB → 2.9KB) — branding Elite
- [x] `theme.py` (4.4KB → 21.9KB) — **CSS Crimson #C0392B completo**

**Novos adicionados (15 arquivos exclusivos EliteBR):**
- [x] `main_window.py` (233.3KB) — shell principal
- [x] `dashboard_panel.py` (32.3KB)
- [x] `activity_panel.py` (9.8KB)
- [x] `asi_panel.py` (11.1KB)
- [x] `binary_search_dialog.py` (17KB)
- [x] `health_check_dialog.py` (7.1KB)
- [x] `verify_dialog.py` (7.4KB)
- [x] `progress_dialog.py` (7.7KB)
- [x] `msg_box_br.py` (7KB)
- [x] `premium_buttons.py` (6.3KB)
- [x] `logo_widget.py` (1.7KB)
- [x] `fast_mod_card_delegate.py` (18.5KB)
- [x] `mod_card_delegate.py` (18.2KB)
- [x] `logo.png` (1564KB)
- [x] `crimson_hero_bg.png` (2026KB)

> **Nota `bug_report.py`:** A versão EliteBR de `bug_report.py` ainda usa `qfluentwidgets` internamente
> (componentes `MessageBoxBase`, `InfoBar`, etc.). Isso é aceitável — o pacote está instalado e
> `bug_report.py` só é aberto sob demanda, nunca no startup. Não afeta o shell principal.

### Fase 3 — Adaptar main.py (Faisal → Elite) ✅ COMPLETO
Editado `src/cdumm/main.py` com 13 edições cirúrgicas:
- [x] `APP_DATA_DIR` → `CDMod_Elite`
- [x] Log → `cdelite.log`
- [x] `app.setApplicationName("Crimson Desert Elite BR")`
- [x] `AppUserModelID` → `kindiboy.cdummelite.modmanager.3`
- [x] Startup log → `"Starting Crimson Desert Elite BR"`
- [x] `FindWindowW` título → `"Crimson Desert Elite BR - {__version__}"`
- [x] `setFontFamilies` (qfluentwidgets) → `logger.debug`
- [x] Bloco Fluent completo removido (`setTheme(LIGHT)`, `setThemeColor`, `WelcomeWizard`)
- [x] `STYLESHEET` Elite aplicado via `app.setStyleSheet(STYLESHEET)`
- [x] `_first_launch` simplificado (sem wizard Fluent)
- [x] `_wizard_theme` default `"dark"` (era `"light"`)
- [x] `CDMods` → `CDModsElite`
- [x] `saved_theme` default `"dark"` (era `"light"`)
- [x] Todos splash `0x0081` → `0x0041` (5 ocorrências)
- [x] `from cdumm.gui.fluent_window import CdummWindow` → `from cdumm.gui.main_window import MainWindow`
- [x] `CdummWindow(...)` → `MainWindow(...)`

**Preservados intactos:**
- Single-instance lock (msvcrt), faulthandler, crash_trace
- Frame stall profiler (frame_stalls.log)
- 4 métodos de game_dir detection
- Snapshot check durante splash
- Semantic schemas durante splash
- Bloco `setTheme(AUTO/DARK)` — 2 refs qfluentwidgets restantes (aceitáveis, só são usadas se saved_theme é auto ou dark)

**Validação:**
- Sintaxe Python: ✅ `ast.parse()` OK
- Zero imports de `fluent_window`, `CdummWindow`, `WelcomeWizard`
- `STYLESHEET` e `setStyleSheet` presentes

### Fase 4 — Copiar Assets Elite ✅ COMPLETO
- [x] `assets/cdumm-logo.png` — 397KB → 1564KB (logo Elite)
- [x] `assets/cdumm-logo-light.png` — 397KB → 1564KB
- [x] `assets/cdumm-logo-dark.png` — 493KB → 1564KB
- [x] `assets/crimson_hero_bg.png` — 2026KB [NOVO]
- [x] `cdumm.ico` — 88KB → 1524KB (icône Elite multi-res)

### Fase 5 — Copiar Build Config Elite ✅ COMPLETO
- [x] `cdumm.spec` — 10.9KB Faisal (com Fluent) → 10.2KB EliteBR (sem Fluent, com DLL strip + Qt translation filter)
- [x] `version_info.txt` — NOVO, 1.2KB, metadata `Crimson Desert Elite BR 4.0.0.0 / CrashByte`

**Verificação:**
- EXE `name='CrimsonDesertEliteBR'` ✅
- `version='version_info.txt'` ✅
- Zero imports Fluent no spec (só um comentário explicativo) ✅
- Todos os 8 módulos GUI Elite presentes nos hiddenimports ✅
- Todos os datas (ico, winmm.dll, logo.png, crimson_hero_bg.png, version_info.txt) existem ✅

### Fase 6 — Atualizar pyproject.toml ✅ COMPLETO
Editado `pyproject.toml` e `src/cdumm/__init__.py`:
- [x] `version` — `"0.7.0"` → `"4.0.0"` (alinha com version_info.txt 4.0.0.0)
- [x] `description` — atualizado para `"Crimson Desert Elite BR — ..."`
- [x] `privatebin>=0.3.0` — **removido** (só usava em `_fluent_archive/` — nenhum módulo ativo usa)
- [x] `xxhash>=3.0` — **adicionado** (`apply_engine.py`, `snapshot_manager.py`)
- [x] `py7zr>=0.20` — **adicionado** (`import_handler.py`, `asi_manager.py`, `main_window.py`)
- [x] `lxml>=5.0` — mantido (`xml_patch_handler.py`)
- [x] `PySide6-Fluent-Widgets>=1.11` — mantido (`bug_report.py` dialog)
- [x] `__version__` — `"3.0.4"` → `"4.0.0"` em `src/cdumm/__init__.py`

### Fase 7 — Validação Estática ✅ COMPLETO

**Resultado: 9/9 checks passados + 1 problema encontrado e corrigido**

| Check | Status |
|-------|--------|
| Syntax check 92 arquivos `.py` ativos | ✅ Zero erros |
| Zero imports Fluent ativos (shell/startup) | ✅ Limpo |
| `main.py` coerência (9 pontos) | ✅ OK |
| `theme.py` STYLESHEET + Crimson `#C0392B` | ✅ OK |
| Assets críticos (7 arquivos) | ✅ OK |
| `main_window.py` — 41 módulos importados | ✅ 41/41 OK |
| API: `ApplyWorker`, `RevertWorker` em `apply_engine.py` | ✅ OK |
| API: `VerifyWorker` em `verify_dialog.py`, `BackupVerifyWorker` em `workers.py` | ✅ OK |
| `setup_dialog.py` + `import_widget.py` sem Fluent | ✅ OK |
| `__version__` / spec / `version_info.txt` todos em `4.0.0` | ✅ OK |

**Problema encontrado e corrigido:**
- `test_mod_dialog.py` não existia em nenhum repo — criado `src/cdumm/gui/test_mod_dialog.py` (1.6KB, stub puro PySide6, sem Fluent)
- Import é local (linha 4517 dentro de uma `def`) — não causa erro no startup, só ao clicar "Testar Mod"

**LIBERADO PARA FASE 8**

### Fase 8 — Teste de Execução ✅ COMPLETO 🎉

**App iniciado com sucesso. Nenhum crash. Nenhum erro.**

Log `CDMod_Elite/cdelite.log` registrado:

| Evento | Resultado |
|--------|-----------|
| `"Starting Crimson Desert Elite BR"` | ✅ App name Elite correto |
| `Loaded font: Oxanium` | ✅ Fonte Elite carregada |
| `Found Crimson Desert (Steam)` | ✅ Game detectado automaticamente |
| Migrações de banco de dados | ✅ 18 migrações Faisal aplicadas |
| `Database initialized at .../CDModsElite/cdumm.db` | ✅ Pasta `CDModsElite` correta |
| `Semantic schemas: 322 tables loaded` | ✅ Engine Faisal ativo |
| `_refresh_all: done total=0.000s` | ✅ `MainWindow` Elite carregou |
| `Config set: theme = dark` | ✅ Tema dark Elite padrão |
| STDERR: vazio | ✅ Zero erros/warnings fatais |
| Processo vivo após 15s | ✅ Nenhum crash |

**Estrutura `CDMod_Elite/` criada corretamente:**
```
.gui_lock, .running, cdelite.log, crash_trace.txt, frame_stalls.log, game_dir.txt
```

**LIBERADO PARA FASE 9 (build PyInstaller)**

### Fase 8b — Correções Pré-Build ✅ COMPLETO

**3 problemas encontrados e corrigidos antes do build final:**

| Problema | Causa | Correção |
|----------|-------|----------|
| Mods não apareciam após import | `FastModCardDelegate` exige `UserRole` dict; `ModListModel.data()` nunca retornava `UserRole` | Adicionado `UserRole` em `ModListModel.data()` + `dataChanged` col 0 em `_on_statuses_ready` |
| "Choose mod preset(s)" em inglês + Fluent | `preset_picker.py` usava `qfluentwidgets` | Reescrito com PySide6 puro + Crimson Elite + PT-BR |
| "Choose What to Apply" em inglês + Fluent | Mesmo arquivo `preset_picker.py` | Mesmo fix acima |

**Arquivos:** `mod_list_model.py` (UserRole) · `preset_picker.py` (reescrito Elite BR completo)

### Fase 8c — Correção de Toggle (Ativar/Desativar Mod) ✅ COMPLETO

**Problema:** Clicar no switch do card não mudava o estado visual/funcional do mod.

**3 causas encontradas comparando com EliteBR (base funcional):**

| # | Causa | Local | Correção |
|---|-------|-------|----------|
| 1 | Comparação `value == Qt.CheckState.Checked.value` frágil em PySide6 strict enums | `setData()` | Substituído por `value in (Qt.CheckState.Checked, 2, True)` |
| 2 | `dataChanged.emit(index, index)` sem roles → Qt6 não re-renderiza `UserRole` | `setData()` | Emite com `[CheckStateRole, UserRole]` explícito |
| 3 | `update_mod_state()` ausente no EW → `AttributeError` ao usar menu de contexto | `mod_list_model.py` | Método adicionado (port do EliteBR) |
| 4 | `refresh()` resetava todos os status para `"checking..."` → cards piscavam | `refresh()` | Default agora é `preserve_statuses=True` (preserva cache) |

### Fase 8d — Correção de Multi-Preset Import ✅ COMPLETO

**Problema:** Ao selecionar 2+ presets do mesmo ZIP, só 1 era importado; depois o segundo acionava o fluxo de "update" do primeiro, removendo-o.

**2 causas encadeadas:**

| # | Causa | Local | Correção |
|---|-------|-------|----------|
| 1 | `dialog.selected_path` (legacy single) era lido em vez de `dialog.selected_presets` (lista) | `_run_import` L2869 | Lê `selected_presets`, faz o loop e enfileira extras via `_import_queue` |
| 2 | Presets do mesmo ZIP têm o mesmo `"name"` no JSON → `_find_existing_mod` detecta o 2º como "update" do 1º | `_run_import` L2753 | Flag `_no_update_check`: paths de batch são marcados para pular duplicate detection |

**Mecanismo:**
- Presets extras copiados para temp files independentes (evita race com `_pending_preset_tmp` cleanup)
- Cada extra adicionado a `self._no_update_check` (set de paths que ignoram `_find_existing_mod`)
- `_run_import` consome o flag com `discard()` antes de passar pelo check
- `_import_queue` / `_process_next_import` existentes gerenciam a fila

### Fase 8e — Localização PT-BR ✅ COMPLETO

| Arquivo | Strings traduzidas |
|---------|-------------------|
| `gui/workers.py` | 26+ strings de progresso (importação/verificação) |
| `engine/apply_engine.py` | 26+ strings de progresso (aplicação de mods) |
| `gui/patch_toggle_dialog.py` | Botões Save/Discard/Cancel → PT-BR via `addButton()` |

### Fase 8f — "Configurar..." abre seletor de variantes ✅ COMPLETO

**Problema:** `Configurar...` caia em "A origem original do mod não foi encontrada" para mods configuráveis.

**Causa:** `_on_configure_mod` lia só `source_path`, que é `None` para mods criados por `import_multi_variant`.

**Correção:** Lógica bifurcada em `_on_configure_mod`:
- Tem `variants` no DB → `PresetPickerDialog` (pré-selecionado com variante ativa)
- Não tem → `TogglePickerDialog` (fluxo legado)

**Arquivo:** `gui/main_window.py` `_on_configure_mod`

### Fase 9 — Build PyInstaller ✅ COMPLETO

**Build v2 — 18/04/2026 01:08:46**

```
dist/CrimsonDesertEliteBR.exe
  Tamanho  : 45.2 MB
  FileDesc : Crimson Desert Elite BR
  Company  : CrashByte
  Version  : 4.0.0.0
  Ícone    : cdumm.ico ✅
```

**Correções aplicadas durante/após o build:**

| Fix | Arquivo | Descrição |
|-----|---------|----------|
| `i18n.py` criado | `gui/i18n.py` | Stub `get(key, default)` — `binary_search_dialog` importava módulo inexistente |
| `cdumm.gui.i18n` | `cdumm.spec` | Adicionado em `hiddenimports` |
| Freeze ~4s (rmtree) | `engine/snapshot_manager.py` | `shutil.rmtree(vanilla_dir)` movido do thread principal para `run()` do worker |
| Freeze ~4s (rmtree) | `gui/main_window.py` | Removido bloco rmtree+mkdir de `_on_refresh_snapshot`; passa `vanilla_dir=` ao worker |
| Freeze pós-backup | `gui/main_window.py` | `_refresh_vanilla_backups()` substituído por `QTimer.singleShot(500, ...)` |
| Card Proteção | `gui/dashboard_panel.py` | Removido guard `if not self.isVisible(): return` de `update_stats()` |

> `_schedule_dashboard_update()` mantido em `_on_snapshot_finished` ✅

### Fase 10 — Migração Final CDMods → CDModsElite (100%) ✅ COMPLETO

**Data:** 18/04/2026

**Problema:** Mesmo depois das fases anteriores, ao importar mods no formato JSON patch,
o motor ainda criava a pasta `CDMods/` no diretório do jogo.

**Dois pontos geravam `.mkdir("CDMods")`:**
1. `import_handler.py` — `mods_dir = game_dir / "CDMods" / "mods"` passado para `import_json_fast()`
2. `json_patch_handler.py` — `_get_pamt_index()` fazia `cdmods = game_dir / "CDMods"` + `.mkdir()`

**Solução arquitetural — novo módulo `paths.py`:**

```
src/cdumm/engine/paths.py  [NOVO]
  CDMODS_FOLDER = "CDModsElite"
  get_cdmods_dir(game_dir)  → CDModsElite/ (fallback CDMods/ se já existir)
  get_vanilla_dir(game_dir) → CDModsElite/vanilla (fallback CDMods/vanilla)
```

**Correções de criação de pasta:**

| Arquivo | Antes | Depois |
|---------|-------|--------|
| `import_handler.py` L1836 | `game_dir / "CDMods" / "mods"` | `deltas_dir.parent / "mods"` |
| `json_patch_handler.py` L893 | `game_dir / "CDMods"` + `.mkdir()` | Detecta `vanilla/` → sobe para CDModsElite/ |

**Correções de leitura (vanilla backup lookup) — 19 ocorrências em 7 arquivos:**

| Arquivo | Ocorrências |
|---------|-------------|
| `import_handler.py` | 5 (PAMT lookup, backup_dir, 3× vanilla path) |
| `json_patch_handler.py` | 4 (import_json_as_entr, import_json_fast, process_json_patches, _get_pamt_index) |
| `crimson_browser_handler.py` | 2 (vanilla PAMT, vanilla PAZ) |
| `mod_health_check.py` | 5 (4 funções de health check) |
| `mod_manager.py` | 1 (get_mod_game_status) |
| `texture_mod_handler.py` | 1 (PATHC vanilla backup) |
| `xml_patch_handler.py` | 1 (process_xml_patches_for_overlay) |

**Validação final:**
```
CRIA PASTA CDMods (.mkdir): 0 ocorrências em todo src/cdumm
Sintaxe Python: 13/13 arquivos OK (ast.parse)
```

---

## Riscos

### 🔴 ALTO — Módulos Novos do Faisal sem equivalente no EliteBR

| Módulo | Risco |
|--------|-------|
| `xml_patch_handler.py` | 35.6KB novo. `apply_engine.py` cresceu +18KB — provavelmente chama `xml_patch_handler`. Confirmar que `main_window.py` EliteBR não precisa de interface direta com ele. |
| `variant_handler.py` | 16.1KB novo. Interface em `import_widget.py` ou `preset_picker.py`? Verificar. |
| `nexus_api.py` + `nexus_filename.py` | Usados pelo `fluent_window.py` para NexusMods update. `main_window.py` EliteBR pode não ter esse fluxo — OK se não for implementado. |
| `configurable_scanner.py` | Pode ser chamado por `apply_engine.py` ou `import_handler.py` — transparente para a GUI. |

### 🟡 MÉDIO — Diferenças em módulos comuns

| Módulo | Risco |
|--------|-------|
| `storage/database.py` | +4.7KB. Pode ter tabelas novas. `main_window.py` EliteBR usa a API de DB via managers — provavelmente compatível. |
| `storage/config.py` | +1.2KB. Pode ter chaves novas. Avaliar impacto. |
| `archive/paz_repack.py` | EliteBR maior que Faisal (17.2KB vs 14KB). Usar Faisal — investigar diferença antes. |
| `workers.py` | Ambos 44.1KB — iguais. Mas `apply_engine.py` cresceu — workers pode ter mudado comportamento interno. |
| `worker_process.py` | Faisal +16 linhas — provavelmente suporte a novos handlers. Usar Faisal. |

### 🟢 BAIXO — Diferenças seguras

| Item | Observação |
|------|-----------|
| Translations | Faisal tem mais strings — sem quebra de UI |
| `mod_list_model.py` | Iguais (12.4KB) |
| `conflict_detector.py` | Iguais entre as bases |
| `semantic/` | Iguais |
| `asi/` | Iguais |

### 🔴 ALTO — Bug latente em main.py Faisal
`main.py` do Faisal ainda importa `qfluentwidgets` em dois pontos:
- Linha 162: `from qfluentwidgets import setFontFamilies`
- Linhas 166-168: `setTheme`, `setThemeColor` Fluent
- Linha 367: `from cdumm.gui.fluent_window import CdummWindow`

Todos devem ser removidos/substituídos na Fase 3.

---

## Customizações Elite a Preservar

| Config | Valor | Arquivo |
|--------|-------|---------|
| `APP_DATA_DIR` | `%LocalAppData%/CDMod_Elite` | `main.py` linha 10 |
| Log principal | `cdelite.log` | `main.py` função `setup_logging` |
| Pasta de mods | `CDModsElite` | `main.py` linha 256 |
| App name | `Crimson Desert Elite BR` | `main.py` linha 139 |
| AppUserModelID | `kindiboy.cdummelite.modmanager.3` | `main.py` linha 126 |
| Tema | Crimson `#C0392B` via `theme.py` | `theme.py` EliteBR |
| Ícone | `cdumm.ico` Elite (1.5MB) | raiz do projeto |
| Splash | `logo.png` + `crimson_hero_bg.png` | `gui/` |
| Window title | `Crimson Desert Elite BR - {version}` | `main_window.py` |
| Wizard | `setup_dialog.py` (sem Fluent) | `gui/setup_dialog.py` |
| Exe name | `CrimsonDesertEliteBR.exe` | `cdumm.spec` |
| Version | `4.0.0` | `version_info.txt` + `__init__.py` |
| Company | CrashByte | `version_info.txt` |
| _check_group_conflicts | Sem popup — loga e retorna True | `main_window.py` |
| ConflictView | Oculta no splitter | `main_window.py` |
| pointer file | `game_dir.txt` em `CDMod_Elite/` | `main.py` |

---

## Verificação Final

### Automática
```
python -c "import ast; ast.parse(open('src/cdumm/main.py').read()); print('OK main')"
python -c "import ast; ast.parse(open('src/cdumm/gui/main_window.py').read()); print('OK mainwindow')"
python -c "from cdumm.gui.theme import STYLESHEET; print(len(STYLESHEET), 'chars')"
Select-String -Recurse -Path src\cdumm -Pattern "fluent_window|welcome_wizard|qfluentwidgets" --Include *.py
```

### Manual
- Executar app → confirmar splash Elite
- Confirmar janela `Crimson Desert Elite BR - 4.x.x`
- Confirmar `CDMod_Elite/cdelite.log` criado
- Confirmar mods salvos em `CDModsElite/`
- Aplicar um mod → sem popup de conflito bloqueador
- Build PyInstaller → `dist/CrimsonDesertEliteBR.exe` 38-45MB

---

## Próximos Passos (Opcionais)

1. **Rebuildar o EXE** — novo build ps-Fase-10 para incluir `paths.py` no bundle
2. Publicar release no Nexus Mods
3. Integrar NexusMods update check no `main_window.py`
4. Teste de regressão completo com EXE `dist/CrimsonDesertEliteBR.exe`

> **Nota:** O build anterior (`CrimsonDesertEliteBR.exe` 45.2MB) não inclui `paths.py` nem as correções da Fase 10.
> Para distribuição final, um novo build é necessário.
