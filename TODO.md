# TODO - Tantivi2Agents

**Poslední aktualizace:** 2025-11-22
**Zdroj:** Komplexní code review z 2025-11-22

---

## 🚨 KRITICKÁ PRIORITA - Bezpečnost (4-6 hodin)

> **VAROVÁNÍ:** Tyto problémy MUSÍ být opraveny před nasazením do produkce!

### 1. Path Traversal při exportu souborů
- [ ] **Přidat validaci výstupních cest v export metodách**
  - Soubor: `tantivy2agents.py`
  - Řádky: 817, 830, 865
  - Čas: 30 minut
  - Dopad: KRITICKÝ - umožňuje přepis libovolných souborů
  - Implementace:
    ```python
    def _validate_output_path(self, output_file):
        abs_path = os.path.abspath(output_file)
        if not abs_path.startswith(os.path.abspath(os.getcwd())):
            raise ValueError("Output file must be within current directory")
        if ".." in output_file:
            raise ValueError("Path traversal not allowed")
        return abs_path
    ```

### 2. Path Traversal přes glob patterny
- [ ] **Validovat všechny glob patterny v konfiguraci**
  - Soubor: `tantivy2agents.py`
  - Řádky: 290, 293, 307, 309
  - Čas: 1 hodina
  - Dopad: KRITICKÝ - umožňuje čtení libovolných souborů
  - Implementace:
    ```python
    def _validate_path_pattern(self, pattern):
        if os.path.isabs(pattern):
            raise ValueError("Absolute paths not allowed")
        if ".." in pattern:
            raise ValueError("Parent directory traversal not allowed")
        return pattern
    ```

### 3. Nebezpečné vytváření symlinků
- [ ] **Přidat validaci při vytváření symlinků**
  - Soubor: `tantivy2agents.py`
  - Řádek: 989
  - Čas: 30 minut
  - Dopad: VYSOKÝ - vytvoření symlinků v systémových adresářích

### 4. Nebezpečné mazání adresářů
- [ ] **Implementovat bezpečnou verzi rmtree s validací**
  - Soubor: `tantivy2agents.py`
  - Řádky: 684, 936, 1178
  - Čas: 45 minut
  - Dopad: VYSOKÝ - smazání libovolných adresářů

### 5. Command Injection v subprocess
- [ ] **Validovat `cwd` parametr v subprocess voláních**
  - Soubor: `tantivy2agents.py`
  - Řádky: 1286, 1297, 1306
  - Čas: 1 hodina
  - Dopad: VYSOKÝ

### 6. Command Injection v bin skriptech
- [ ] **Použít absolutní cesty místo relativních v bin/tantivy-search**
  - Soubor: `bin/tantivy-search`
  - Řádky: 85-89
  - Čas: 30 minut
  - Dopad: VYSOKÝ

### 7. Kontroly velikosti souborů
- [ ] **Přidat limity pro velikost souborů před načtením do paměti**
  - Soubor: `tantivy2agents.py`
  - Řádky: 359, 388, 513, 1202
  - Čas: 30 minut
  - Dopad: STŘEDNÍ - DoS přes velké soubory

---

## ⚡ VYSOKÁ PRIORITA - Správnost kódu (6-8 hodin)

### 8. Duplicitní importy
- [ ] **Odstranit duplicitní import fnmatch**
  - Soubor: `tantivy2agents.py`
  - Řádek: 428
  - Čas: 5 minut

- [ ] **Odstranit všechny method-level importy**
  - Soubor: `tantivy2agents.py`
  - Řádky: 795, 796, 825-827, 862, 867, 1375
  - Čas: 10 minut

### 9. Neplatné Tantivy API použití
- [ ] **Opravit nebo odstranit len(searcher) volání**
  - Soubor: `tantivy2agents.py`
  - Řádek: 1439
  - Čas: 30 minut
  - Poznámka: Searcher nepodporuje len(), použít správné API

### 10. Bare except klauzule (16 výskytů)
- [ ] **Nahradit bare except specifickými exceptions**
  - Soubor: `tantivy2agents.py`
  - Řádky: 368, 397, 502, 538, 541, 562, 575, 647, 764, 1243, 1368, 1441, 1486
  - Čas: 2 hodiny
  - Dopad: VYSOKÝ - skrývá kritické chyby
  - Vzor:
    ```python
    # Místo:
    except:
        pass

    # Použít:
    except (SpecificError1, SpecificError2) as e:
        logging.debug(f"Description: {e}")
    ```

### 11. Type hints
- [ ] **Přidat type hints k všem public metodám**
  - Soubor: `tantivy2agents.py`
  - Všechny metody TantivyAgent třídy
  - Čas: 3 hodiny
  - Dopad: VYSOKÝ - zlepší maintainability a IDE support
  - Příklad:
    ```python
    from typing import Optional, List, Dict, Any, Tuple

    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from JSON file with defaults"""

    def _get_files_for_indexing(self, show_dirs: bool = False,
                                show_files: bool = False) -> Tuple[List[str], List[str]]:
        """Get list of files to index"""
    ```

### 12. Chybějící LICENSE soubor
- [ ] **Vytvořit LICENSE soubor s MIT licencí**
  - Nový soubor: `LICENSE`
  - Čas: 10 minut
  - Dopad: VYSOKÝ - právní požadavek
  - Poznámka: README zmiňuje MIT License, ale soubor chybí

### 13. Config dokumentace
- [ ] **Opravit nesrovnalost v příkladech konfigurace**
  - Soubor: `README.md`, `examples/.tantivi2agents.json`
  - Čas: 15 minut
  - Problém: Příklady ukazují `.tantivi2agents`, ale default je `.tantivy-data`

---

## 🔧 STŘEDNÍ PRIORITA - Technický dluh (12-15 hodin)

### 14. Duplicitní kód - Hook Installation
- [ ] **Sloučit _install_claude_hooks_in_target() a _install_claude_hooks()**
  - Soubor: `tantivy2agents.py`
  - Řádky: 1024-1075 vs 1107-1159
  - Čas: 30 minut
  - Úspora: 50+ řádků kódu

### 15. Mrtvý kód - bin/ adresář
- [ ] **ODSTRANIT celý bin/ adresář**
  - Adresář: `bin/`
  - Soubory: tantivy-search, tantivy-index, tantivy-hook, tantivy-clear
  - Čas: 15 minut
  - Úspora: 319 řádků mrtvého kódu
  - Důvod: Používá staré cesty, není dokumentováno, jiná implementace

### 16. Dlouhé metody
- [ ] **Refaktorovat _get_files_for_indexing (102 řádků)**
  - Soubor: `tantivy2agents.py`
  - Řádky: 322-424
  - Čas: 1 hodina
  - Rozdělit na: _expand_patterns, _filter_files, _apply_exclusions

- [ ] **Refaktorovat status_command (132 řádků)**
  - Soubor: `tantivy2agents.py`
  - Řádky: 1371-1503
  - Čas: 1 hodina
  - Rozdělit na: _get_index_stats, _check_index_health, _display_status

- [ ] **Refaktorovat encoding_info_command (92 řádků)**
  - Soubor: `tantivy2agents.py`
  - Řádky: 1180-1272
  - Čas: 45 minut

- [ ] **Refaktorovat setup_command (97 řádků)**
  - Soubor: `tantivy2agents.py`
  - Řádky: 1273-1370
  - Čas: 45 minut

### 17. JSON Schema validace
- [ ] **Přidat validaci konfigurace pomocí jsonschema**
  - Soubor: `tantivy2agents.py`
  - Metoda: `_load_config`
  - Čas: 1 hodina
  - Závislost: Přidat `jsonschema` do requirements.txt

### 18. Structured Logging
- [ ] **Implementovat logging framework**
  - Soubor: `tantivy2agents.py`
  - Čas: 2 hodiny
  - Nahradit print() calls s logging
  - Přidat logging levels (DEBUG, INFO, WARNING, ERROR)

### 19. Chybějící test cases
- [ ] **Přidat testy pro error cases**
  - Soubor: `tests/test_basic.py`
  - Čas: 2 hodiny
  - Nové testy:
    - `test_malformed_config()`
    - `test_permission_denied()`
    - `test_corrupted_index()`
    - `test_large_file_handling()`
    - `test_invalid_query_syntax()`

- [ ] **Přidat testy pro edge cases**
  - Soubor: `tests/test_encoding.py`
  - Čas: 1 hodina
  - Nové testy:
    - `test_high_confidence_detection()`
    - `test_binary_with_text_content()`

### 20. Test duplicity
- [ ] **Vytvořit pytest fixture pro TantivyAgent import**
  - Nový soubor: `tests/conftest.py`
  - Čas: 30 minut
  - Odstranit duplicitní import kód z 7 míst v test_basic.py

### 21. Dependency update
- [ ] **Aktualizovat PyYAML na nejnovější verzi**
  - Soubor: `requirements.txt`
  - Čas: 30 minut
  - Současná: 6.0.2 → Nová: 6.0.3+ (security fix)
  - Spustit všechny testy po update

### 22. CHANGELOG
- [ ] **Vytvořit CHANGELOG.md**
  - Nový soubor: `CHANGELOG.md`
  - Čas: 1 hodina
  - Dokumentovat historii změn z git logu

### 23. CONTRIBUTING guide
- [ ] **Vytvořit CONTRIBUTING.md**
  - Nový soubor: `CONTRIBUTING.md`
  - Čas: 1 hodina
  - Odkazy na .claude/CLAUDE.md pravidla
  - Vývojářský workflow

---

## 🏗️ DLOUHODOBÉ - Architektura (30-40 hodin)

### 24. Modulární struktura
- [ ] **Rozdělit monolitický soubor do modulů**
  - Čas: 12 hodin
  - Vytvořit package strukturu:
    ```
    tantivy2agents/
    ├── __init__.py
    ├── config/
    │   ├── __init__.py
    │   ├── loader.py
    │   └── defaults.py
    ├── core/
    │   ├── __init__.py
    │   ├── scanner.py
    │   ├── indexer.py
    │   ├── searcher.py
    │   └── parser.py
    ├── encoding/
    │   ├── __init__.py
    │   └── detector.py
    ├── export/
    │   ├── __init__.py
    │   └── exporters.py
    ├── install/
    │   ├── __init__.py
    │   └── installer.py
    ├── cli/
    │   ├── __init__.py
    │   └── commands.py
    └── main.py
    ```

### 25. Dependency Injection
- [ ] **Implementovat DI pattern**
  - Čas: 4 hodiny
  - Odstranit tight coupling
  - Zlepšit testovatelnost

### 26. Tantivy Abstraction Layer
- [ ] **Vytvořit TantivyRepository abstrakci**
  - Čas: 3 hodiny
  - Odstranit přímé Tantivy volání z business logiky
  - Zlepšit testovatelnost

### 27. Config management
- [ ] **Přesunout default config do samostatného souboru**
  - Nový soubor: `tantivy2agents/config/defaults.json`
  - Čas: 1 hodina
  - Odstranit 70+ řádků inline config z kódu

### 28. Environment variables
- [ ] **Přidat podporu pro environment variables**
  - Čas: 2 hodiny
  - Proměnné:
    - `TANTIVY_INDEX_DIR`
    - `TANTIVY_CONFIG_PATH`
    - `TANTIVY_PROJECT_ROOT`

---

## 🎯 VOLITELNÉ - Rozšíření

### 29. Performance optimalizace
- [ ] **Implementovat parallel file scanning**
  - Čas: 4 hodiny
  - Použít multiprocessing pro velké projekty

- [ ] **Přidat index optimization po build**
  - Čas: 2 hodiny
  - Volat Tantivy merge/optimize

### 30. Plugin systém
- [ ] **Vytvořit plugin systém pro exporters**
  - Čas: 6 hodin
  - Umožnit custom export formáty

### 31. Async support
- [ ] **Přidat async/await pro I/O operace**
  - Čas: 8 hodin
  - Použít asyncio pro file operations

---

## 📋 Rychlé výhry (< 2 hodiny celkem)

> Tyto úkoly mají vysoký dopad a nízké náklady

- [ ] **#21: Aktualizovat PyYAML** (10 min) → Bezpečnostní fix
- [ ] **#15: Odstranit bin/ adresář** (15 min) → -319 řádků
- [ ] **#14: Sloučit hook metody** (30 min) → -50 řádků
- [ ] **#8: Odstranit duplicitní importy** (15 min) → Cleanup
- [ ] **#12: Přidat LICENSE** (10 min) → Právní požadavek
- [ ] **#13: Opravit config docs** (15 min) → Dokumentace

**Celkový čas:** 1.5 hodiny
**Celkový dopad:** Bezpečnostní update + odstranění 370+ řádků kódu

---

## 📊 Plán podle priorit

### Fáze 1: Bezpečnost (Týden 1)
**Čas:** 4-6 hodin
**Úkoly:** #1-7
**Výstup:** Bezpečná aplikace připravená pro produkci

### Fáze 2: Kvalita (Týden 2-3)
**Čas:** 6-8 hodin
**Úkoly:** #8-13
**Výstup:** Čistý, správný kód s type hints

### Fáze 3: Udržovatelnost (Měsíc 1)
**Čas:** 12-15 hodin
**Úkoly:** #14-23
**Výstup:** Udržovatelný projekt s nízkim technickým dluhem

### Fáze 4: Architektura (Měsíc 2-3)
**Čas:** 30-40 hodin
**Úkoly:** #24-28
**Výstup:** Modulární, škálovatelná architektura

---

## 🎯 Milestones

### Milestone 1: Produkční nasazení
- ✅ Všechny kritické bezpečnostní problémy opraveny (#1-7)
- ✅ Kritické chyby kódu opraveny (#8-11)
- ✅ LICENSE soubor přidán (#12)
- **ETA:** 10-14 hodin
- **Stav:** READY FOR DEPLOYMENT

### Milestone 2: Kvalitní kódová báze
- ✅ Milestone 1 dokončen
- ✅ Type hints přidány (#11)
- ✅ Technický dluh odstraněn (#14-20)
- ✅ Dokumentace kompletní (#22-23)
- **ETA:** 24-29 hodin
- **Stav:** HIGH QUALITY CODEBASE

### Milestone 3: Škálovatelná architektura
- ✅ Milestone 2 dokončen
- ✅ Modulární struktura (#24)
- ✅ Dependency injection (#25)
- ✅ Abstraction layers (#26)
- **ETA:** 54-69 hodin
- **Stav:** SCALABLE ARCHITECTURE

---

## 📈 Tracking

### Statistiky
- **Celkový počet úkolů:** 31
- **Kritické:** 7 (bezpečnost)
- **Vysoké:** 6 (kvalita kódu)
- **Střední:** 10 (technický dluh)
- **Dlouhodobé:** 5 (architektura)
- **Volitelné:** 3 (rozšíření)

### Časový odhad
- **Minimální (produkce):** 10-14 hodin (Fáze 1+2 kritické)
- **Doporučený (kvalita):** 22-29 hodin (Fáze 1+2+3)
- **Plný refactoring:** 52-69 hodin (všechny fáze)

---

**Poslední aktualizace:** 2025-11-22
**Next review:** Po dokončení Fáze 1 (bezpečnost)
