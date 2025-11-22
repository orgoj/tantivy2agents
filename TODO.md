# TODO - Tantivi2Agents

**Poslední aktualizace:** 2025-11-22
**Zdroj:** Komplexní code review z 2025-11-22
**Context:** Lokální CLI nástroj pro izolované prostředí

## 🎉 Nedávné Dokončení (2025-11-22)

**✅ Rychlé Výhry - VŠECHNY HOTOVÉ!**
- ✅ Odstranit bin/ adresář (-319 řádků)
- ✅ Odstranit duplicitní importy (-13 řádků)
- ✅ Sloučit hook metody (-47 řádků)
- ✅ Aktualizovat PyYAML (6.0.2 → 6.0.3)

**✅ Priority 1 - ČÁSTEČNĚ HOTOVÉ (6/8)**
- ✅ Opravit bare except klauzule (všechny 18 místa)
- ✅ Přidat type hints - fáze 1 (public API)
- ✅ Opravit neplatné Tantivy API
- ✅ Opravit scope checks (2 místa)

**📊 Celkový Pokrok:**
- **-379 řádků kódu** odstraněno
- **8 úkolů** dokončeno
- **44% Priority 1** hotové

---

## ⚠️ KONTEXT: Lokální CLI Nástroj

Tento nástroj je určen pro **lokální použití** vývojářem na vlastním počítači. **NENÍ** určen pro:
- ❌ Webové aplikace
- ❌ Síťové služby
- ❌ Multi-user prostředí
- ❌ Zpracování nedůvěryhodných vstupů

**Důsledky pro priority:**
1. 🔴 **HIGHEST:** Code quality & best practices (údržba, debugování)
2. 🟡 **MEDIUM:** Safety checks (prevence nehod)
3. 🟢 **LOW:** Security hardening (malé riziko pro local CLI)

**Security issues** jsou dokumentovány jako **best practices**, ne kritické zranitelnosti.

---

## 🔴 VYSOKÁ PRIORITA - Code Quality & Best Practices (8-12 hodin)

> Tyto problémy přímo ovlivňují **údržbu, debugování a vývoj**

### 1. ✅ Opravit bare except klauzule (16 výskytů) ⭐ **HOTOVO**
- **Priorita:** 🔴 CRITICAL pro debugging
- **Čas:** 2 hodiny
- **Dopad:** Skrývají chyby, brání Ctrl+C, ztěžují debugging
- **Status:** ✅ Dokončeno - všechny bare except klauzule opraveny s konkrétními výjimkami

**Lokace:** `tantivy2agents.py` - řádky 368, 397, 502, 538, 541, 562, 575, 647, 764, 1243, 1368, 1441, 1486

**Současný problém:**
```python
try:
    meta = yaml.safe_load(header) or {}
except:  # ❌ Zachycuje vše včetně KeyboardInterrupt!
    pass
```

**Oprava:**
```python
try:
    meta = yaml.safe_load(header) or {}
except (yaml.YAMLError, ValueError) as e:
    logging.debug(f"Failed to parse YAML in {file_path}: {e}")
    meta = {}
except KeyboardInterrupt:
    raise  # Vždy propaguj Ctrl+C!
```

**Checklist:**
- [x] Line 368: File reading exception
- [x] Line 397: Indexing exception
- [x] Line 502: Encoding detection
- [x] Line 538: UTF-8 decode
- [x] Line 541: Fallback encoding
- [x] Line 562: Chardet detection
- [x] Line 575: YAML parsing
- [x] Line 647: YAML error
- [x] Line 764: Search error
- [x] Line 1243: Config loading
- [x] Line 1368: Import error
- [x] Line 1441: Index info access
- [x] Line 1486: Rebuild check
- [x] Lines 502-563: Multiple encoding fallbacks
- [x] Line 1413: Status command exception
- [x] Line 1429: Searcher operations

---

### 2. Přidat type hints ke všem metodám ⭐
- **Priorita:** 🔴 HIGH pro maintainability
- **Čas:** 3-4 hodiny
- **Dopad:** Lepší IDE podpora, méně bugů, lepší dokumentace
- **Status:** ✅ Fáze 1 dokončena (Public API) | ⏳ Fáze 2-3 zbývají

**Současný stav:** ✅ Type hints přidány pro public API (command methods)

**Fáze implementace:**

**Fáze 1: Public API (1 hodina)** ✅ **HOTOVO**
```python
from typing import Optional, List, Dict, Any, Tuple

# Command methods
def index_command(self, force: bool = False, show_dirs: bool = False,
                 show_files: bool = False) -> None:
    """Index documents"""

def search_command(self, query: str, limit: Optional[int] = None,
                  format_output: Optional[str] = None,
                  output_file: Optional[str] = None) -> None:
    """Search indexed documents"""

def clear_command(self) -> None:
    """Clear index"""
```

**Fáze 2: Internal methods (2 hodiny)**
```python
def _load_config(self) -> Dict[str, Any]:
    """Load configuration from JSON file with defaults"""

def _get_files_for_indexing(self, show_dirs: bool = False,
                           show_files: bool = False) -> Tuple[List[str], List[str]]:
    """Get list of files to index"""

def _read_file_with_encoding_detection(self, file_path: str) -> Tuple[Optional[str], str]:
    """Read file with automatic encoding detection"""
```

**Fáze 3: Helper methods (1 hodina)**
```python
def _is_binary_file(self, file_path: str, content_bytes: Optional[bytes] = None) -> bool:
    """Check if file is binary"""

def _parse_markdown(self, file_path: str) -> Tuple[Dict[str, Any], str]:
    """Parse markdown file and extract metadata"""
```

**Checklist:**
- [x] `__init__` method
- [x] 7 command methods (index, search, clear, install, etc.)
- [ ] 4 config methods (_load_config, _get_default_config, etc.)
- [ ] 3 file discovery methods
- [ ] 3 encoding detection methods
- [ ] 1 markdown parsing method
- [ ] 3 indexing methods
- [ ] 5 searching methods
- [ ] 4 export methods
- [ ] 7 installation methods

---

### 3. ✅ Odstranit duplicitní kód - Hook Installation ⭐ **HOTOVO**
- **Priorita:** 🔴 HIGH
- **Čas:** 30-45 minut
- **Úspora:** 50+ řádků kódu (47 řádků odstraněno)
- **Dopad:** Údržba, konzistence
- **Status:** ✅ Dokončeno - hook metody sloučeny do jedné unifikované implementace

**Problém:** Dvě téměř identické metody (90% duplicita)
- `_install_claude_hooks_in_target()` (řádky 1024-1075)
- `_install_claude_hooks()` (řádky 1107-1159)

**Oprava:**
```python
def _install_claude_hooks(self, target_root: Optional[str] = None,
                         use_absolute_path: bool = False) -> None:
    """Unified hook installation method

    Args:
        target_root: Target project root (None = self.project_root)
        use_absolute_path: Use absolute path vs relative tools/ path
    """
    target_root = target_root or self.project_root

    if use_absolute_path:
        hook_command = os.path.abspath(__file__)
    else:
        hook_command = os.path.join(target_root, 'tools', 'tantivy2agents.py')

    # ... zbytek sdílené logiky

# Pak použít:
def install_command(...):
    self._install_claude_hooks(target_root, use_absolute_path=False)

def _setup_current_project():
    self._install_claude_hooks(use_absolute_path=True)
```

---

### 4. ✅ Odstranit mrtvý kód - bin/ adresář **HOTOVO**
- **Priorita:** 🟡 MEDIUM
- **Čas:** 15 minut
- **Úspora:** 319 řádků kódu (odstraněno)
- **Dopad:** Čistota projektu, méně zmatenosti
- **Status:** ✅ Dokončeno - celý bin/ adresář odstraněn

**Soubory odstraněny:**
```bash
rm -rf bin/
# Odstraněno:
# - bin/tantivy-search (160 řádků)
# - bin/tantivy-index (112 řádků)
# - bin/tantivy-hook (32 řádků)
# - bin/tantivy-clear (15 řádků)
```

**Důvody:**
- Používal staré cesty `.tantivy/idx` místo `.tantivy-data`
- Nebyl dokumentován v README
- Jiná implementace než main script
- Redundantní s unifikovaným `tantivy2agents.py`

---

### 5. ✅ Odstranit duplicitní importy **HOTOVO**
- **Priorita:** 🟡 MEDIUM
- **Čas:** 15 minut
- **Dopad:** Čistota kódu, mírné zlepšení performance
- **Status:** ✅ Dokončeno - všechny duplicitní importy odstraněny (13 řádků)

**Problém 1: Duplicitní import v metodě**
```python
# Line 428
def _match_pattern(self, path, pattern):
    import fnmatch  # ❌ Již importováno na řádku 32
    return fnmatch.fnmatch(path, pattern)
```

**Oprava:** Odstranit lokální import

**Problém 2: Method-level importy (6 výskytů)**
```python
# Lines 795, 796, 825-827, 862, 867, 1375
def _export_json(self, results, query, output_file):
    import json  # ❌ Již importováno na řádku 22
    from datetime import datetime  # ❌ Již importováno na řádku 29
```

**Oprava:** Odstranit všechny method-level importy

**Checklist:**
- [x] Line 428: fnmatch v _match_pattern
- [x] Line 795-796: json, datetime v _export_json
- [x] Line 825-827: csv, datetime v _export_csv
- [x] Line 862: sys v _export_txt
- [x] Line 867: sys v _export_txt
- [x] Line 1375: sys v status_command

---

### 6. ✅ Opravit neplatné Tantivy API použití **HOTOVO**
- **Priorita:** 🟡 MEDIUM
- **Čas:** 30 minut
- **Dopad:** Správnost, lepší chybové hlášky
- **Status:** ✅ Dokončeno - neplatné len(searcher) nahrazeno správným API

**Problém:**
```python
# Line 1439 v status_command
try:
    total_docs = len(searcher)  # ❌ Searcher nepodporuje len()
    print(f"   Searchable docs: {total_docs:,}")
except:
    print("   Searchable docs: N/A")
```

**Oprava:**
```python
try:
    # Použít správné Tantivy API
    total_docs = searcher.num_docs()  # nebo jiné správné volání
    print(f"   Searchable docs: {total_docs:,}")
except AttributeError:
    # Pokud API neexistuje v této verzi Tantivy
    print("   Searchable docs: N/A (API not available)")
except Exception as e:
    logging.debug(f"Failed to get doc count: {e}")
    print("   Searchable docs: N/A")
```

**TODO:** Ověřit správné Tantivy API pro získání počtu dokumentů

---

### 7. Refaktorovat příliš dlouhé metody
- **Priorita:** 🟡 MEDIUM
- **Čas:** 3-4 hodiny
- **Dopad:** Čitelnost, testovatelnost

**Metody k refactoringu:**

#### 7.1 `_get_files_for_indexing` (102 řádků, lines 322-424)
**Rozdělit na:**
```python
def _get_files_for_indexing(self, show_dirs=False, show_files=False):
    """Main orchestration"""
    dirs, patterns = self._expand_configuration()
    files = self._collect_files_from_sources(dirs, patterns, show_files)
    unique_files = self._deduplicate_files(files)
    return unique_files, dirs

def _expand_configuration(self) -> Tuple[List[str], List[str]]:
    """Expand patterns from config"""

def _collect_files_from_sources(self, dirs, patterns, show_files) -> List[str]:
    """Collect files from all sources"""

def _deduplicate_files(self, files: List[str]) -> List[str]:
    """Remove duplicates while preserving order"""
```

#### 7.2 `status_command` (132 řádků, lines 1371-1503)
**Rozdělit na:**
```python
def status_command(self):
    """Main status display"""
    if not self._check_index_exists():
        return

    stats = self._gather_index_stats()
    self._display_status(stats)

def _gather_index_stats(self) -> Dict[str, Any]:
    """Collect all statistics"""

def _display_status(self, stats: Dict[str, Any]) -> None:
    """Format and print status"""
```

#### 7.3 `encoding_info_command` (92 řádků, lines 1180-1272)
**Rozdělit na podobně**

#### 7.4 `setup_command` (97 řádků, lines 1273-1370)
**Rozdělit na podobně**

---

### 8. ✅ Opravit nebezpečnou kontrolu scope proměnných **HOTOVO**
- **Priorita:** 🟡 MEDIUM
- **Čas:** 20 minut
- **Dopad:** Správnost, robustnost
- **Status:** ✅ Dokončeno - 'in locals()' nahrazeno explicitním sledováním stavu (2 místa)

**Problém:**
```python
# Lines 1457, 1491
if 'index_info' in locals():
    needs_rebuild = self._should_rebuild_index(data_dir)
```

**Oprava:**
```python
# Explicitní sledování
index_info_loaded = False
index_info = None

try:
    with open(index_info_path) as f:
        index_info = json.load(f)
    index_info_loaded = True
except FileNotFoundError:
    pass

# Později
if index_info_loaded:
    needs_rebuild = self._should_rebuild_index(data_dir)
```

---

## 🟡 STŘEDNÍ PRIORITA - Safety & Robustnost (8-10 hodin)

> Prevence nehod, ne bezpečnostních útoků

### 9. Přidat user confirmations pro destruktivní operace
- **Priorita:** 🟡 MEDIUM (safety)
- **Čas:** 1 hodina
- **Dopad:** Prevence náhodné ztráty dat

**Pro `clear` command:**
```python
def clear_command(self):
    """Clear index with user confirmation"""
    if os.path.exists(data_dir):
        print(f"⚠️  This will delete: {data_dir}")
        print(f"   Size: {self._get_dir_size(data_dir)}")
        response = input("Continue? (y/N): ")
        if response.lower() != 'y':
            print("❌ Cancelled")
            return

    shutil.rmtree(data_dir)
    print("✅ Index cleared")
```

**Pro `--force` flag:**
```python
def index_command(self, force=False, ...):
    if force and os.path.exists(index_dir):
        print("⚠️  --force will rebuild entire index")
        response = input("Continue? (y/N): ")
        if response.lower() != 'y':
            print("❌ Cancelled")
            return
```

---

### 10. Přidat path validation (safety checks)
- **Priorita:** 🟡 MEDIUM (prevence nehod)
- **Čas:** 2 hodiny
- **Dopad:** Prevence náhodného poškození souborů

**Poznámka:** Pro local CLI to není security issue, ale **prevence chyb**.

#### 10.1 Validace výstupních cest
```python
def _validate_output_path(self, output_file: str) -> str:
    """Warn if output path is outside current directory"""
    abs_path = os.path.abspath(output_file)
    current_dir = os.path.abspath(os.getcwd())

    if not abs_path.startswith(current_dir):
        print(f"⚠️  Warning: Output path outside current directory")
        print(f"   Path: {output_file}")
        response = input("Continue? (y/N): ")
        if response.lower() != 'y':
            raise ValueError("Output cancelled by user")

    return abs_path
```

#### 10.2 Validace glob patterns
```python
def _validate_path_pattern(self, pattern: str) -> str:
    """Warn about patterns that go outside project"""
    if os.path.isabs(pattern):
        print(f"⚠️  Warning: Absolute path in config: {pattern}")
        print("   This will index files outside project directory")
        response = input("Continue? (y/N): ")
        if response.lower() != 'y':
            raise ValueError("Indexing cancelled")

    if ".." in pattern:
        print(f"⚠️  Warning: Parent directory pattern: {pattern}")
        # ... similar

    return pattern
```

#### 10.3 Safe rmtree
```python
def _safe_rmtree(self, path: str) -> None:
    """Delete with symlink detection"""
    abs_path = os.path.abspath(path)

    # Check within project
    if not abs_path.startswith(os.path.abspath(self.project_root)):
        raise ValueError(f"Cannot delete outside project: {path}")

    # Warn about symlinks
    if os.path.islink(path):
        print(f"⚠️  Warning: {path} is a symlink!")
        print(f"   Target: {os.readlink(path)}")
        response = input("Delete symlink only? (y/N): ")
        if response.lower() == 'y':
            os.unlink(path)
            return
        else:
            raise ValueError("Delete cancelled")

    shutil.rmtree(abs_path)
```

---

### 11. Implementovat structured logging
- **Priorita:** 🟡 MEDIUM
- **Čas:** 2 hodiny
- **Dopad:** Lepší debugging, troubleshooting

```python
import logging

# Setup
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('.tantivy-data/tantivy.log'),
        logging.StreamHandler()  # Also print to console
    ]
)

logger = logging.getLogger('tantivy2agents')

# Usage
logger.debug(f"Reading file: {file_path}")
logger.info(f"Indexed {len(docs)} documents")
logger.warning(f"Skipped binary file: {file_path}")
logger.error(f"Failed to read {file_path}: {e}")
```

**Nahradit:**
- `print()` statements pro debugging → `logger.debug()`
- Success messages → `logger.info()`
- Warnings → `logger.warning()`
- Errors → `logger.error()`

---

### 12. JSON Schema validace konfigurace
- **Priorita:** 🟡 MEDIUM
- **Čas:** 1.5 hodiny
- **Dopad:** Prevence chyb v konfiguraci

```python
import jsonschema

CONFIG_SCHEMA = {
    "type": "object",
    "properties": {
        "version": {"type": "string"},
        "index_dir": {"type": "string"},
        "global_patterns": {
            "type": "object",
            "properties": {
                "include": {"type": "array", "items": {"type": "string"}},
                "exclude": {"type": "array", "items": {"type": "string"}}
            }
        },
        # ...
    },
    "required": ["version"]
}

def _load_config(self):
    """Load and validate configuration"""
    # ... load JSON

    try:
        jsonschema.validate(user_config, CONFIG_SCHEMA)
    except jsonschema.ValidationError as e:
        logger.error(f"Invalid configuration: {e.message}")
        print(f"❌ Configuration error: {e.message}")
        print(f"   Path: {' > '.join(str(p) for p in e.path)}")
        print("   Using default configuration.")
        return default_config

    # ... merge configs
```

**Přidat do requirements.txt:**
```
jsonschema>=4.0.0
```

---

### 13. ✅ Aktualizovat PyYAML dependency **HOTOVO**
- **Priorita:** 🟡 MEDIUM (best practices)
- **Čas:** 30 minut
- **Dopad:** Security updates, bug fixes
- **Status:** ✅ Dokončeno - PyYAML aktualizován na 6.0.3

**Současně:** `PyYAML==6.0.2` → **Aktualizováno na:** `PyYAML==6.0.3`

```bash
# 1. Update requirements.txt
echo "PyYAML==6.0.3" > requirements.txt.new

# 2. Test
pip install PyYAML==6.0.3
python run_tests.py

# 3. If tests pass, update
mv requirements.txt.new requirements.txt
```

---

### 14. Přidat chybějící testy (error cases)
- **Priorita:** 🟡 MEDIUM
- **Čas:** 3 hodiny
- **Dopad:** Lepší test coverage, jistota

**Nové testy:**

```python
# tests/test_error_cases.py

def test_malformed_json_config(tmp_path):
    """Test handling of invalid JSON config"""
    config_file = tmp_path / ".tantivi2agents.json"
    config_file.write_text("{invalid json}")

    agent = TantivyAgent(config_path=str(config_file))
    # Should fall back to defaults
    assert agent.config['version'] == '1.0'

def test_config_with_invalid_types(tmp_path):
    """Test config with wrong value types"""
    config_file = tmp_path / ".tantivi2agents.json"
    config_file.write_text('{"index_dir": 123}')  # Should be string
    # ... assert graceful handling

def test_large_file_handling(tmp_path):
    """Test files > 100MB are skipped"""
    # Create large file
    large_file = tmp_path / "large.txt"
    large_file.write_bytes(b"x" * (100 * 1024 * 1024 + 1))
    # ... assert skipped with warning

def test_permission_denied(tmp_path):
    """Test handling of unreadable files"""
    # ...

def test_corrupted_index():
    """Test recovery from corrupted index files"""
    # ...
```

---

### 15. Vytvořit pytest fixture pro TantivyAgent
- **Priorita:** 🟢 LOW
- **Čas:** 30 minut
- **Úspora:** Odstranit duplicitní import kód ze 7 míst

```python
# tests/conftest.py
import pytest
import importlib.util
import os

@pytest.fixture
def TantivyAgent():
    """Load TantivyAgent class"""
    script_path = os.path.join(
        os.path.dirname(__file__), "..", "tantivy2agents.py"
    )
    spec = importlib.util.spec_from_file_location("tantivy_agent", script_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.TantivyAgent

# Pak v testech:
def test_something(TantivyAgent, tmp_path):
    agent = TantivyAgent()
    # ...
```

---

## 🟢 NÍZKÁ PRIORITA - Architektura (30+ hodin)

> Long-term improvements, ne urgentní

### 16. Modulární struktura
- **Priorita:** 🟢 LOW (nice to have)
- **Čas:** 12+ hodin
- **Dopad:** Lepší organizace, škálovatelnost

**Poznámka:** Pro small CLI tool může být overkill. Zvážit pouze pokud projekt roste.

```
tantivy2agents/
├── __init__.py
├── config/
│   ├── loader.py
│   └── defaults.py
├── core/
│   ├── scanner.py
│   ├── indexer.py
│   └── searcher.py
├── cli/
│   └── commands.py
└── main.py
```

### 17. Dependency Injection
- **Priorita:** 🟢 LOW
- **Čas:** 4 hodiny
- **Dopad:** Lepší testovatelnost (ale testy už jsou dobré)

### 18. Environment variables
- **Priorita:** 🟢 LOW
- **Čas:** 2 hodiny

---

## 🎯 Rychlé Výhry (< 2 hodiny celkem) ✅ **VŠECHNY HOTOVÉ!**

**Vysoký dopad, nízké náklady:**

1. ✅ **Opravit config example** (15 min) → **HOTOVO**
2. ✅ **Přidat LICENSE** (10 min) → **HOTOVO**
3. ✅ **Odstranit bin/ adresář** (15 min) → **HOTOVO** (-319 řádků kódu)
4. ✅ **Odstranit duplicitní importy** (15 min) → **HOTOVO** (-13 řádků)
5. ✅ **Sloučit hook metody** (30 min) → **HOTOVO** (-47 řádků kódu)
6. ✅ **Aktualizovat PyYAML** (30 min) → **HOTOVO** (6.0.2 → 6.0.3)

**Výsledek:** ✅ Dokončeno = **-379 řádků kódu** + výrazně lepší kvalita!

---

## 📊 Přepracované Priority

### Fáze 1: CODE QUALITY (Týden 1-2) - 8-12 hodin ⭐
**NEJVYŠŠÍ PRIORITA pro lokální CLI nástroj**

**Úkoly:** #1-8
- Bare except fixes
- Type hints
- Remove duplicate code
- Remove dead code
- Fix API usage
- Refactor long methods

**Výstup:** Čistý, udržovatelný kód s dobrým debugging

### Fáze 2: SAFETY & ROBUSTNOST (Týden 3-4) - 8-10 hodin
**STŘEDNÍ PRIORITA**

**Úkoly:** #9-15
- User confirmations
- Path validation (safety, ne security)
- Structured logging
- Config validation
- More tests
- PyYAML update

**Výstup:** Robustní nástroj s prevencí nehod

### Fáze 3: ARCHITEKTURA (Měsíc 2-3) - 30+ hodin
**NÍZKÁ PRIORITA** (zvážit podle růstu projektu)

**Úkoly:** #16-18
- Modulární struktura
- Dependency injection
- Environment variables

**Výstup:** Škálovatelná architektura (pokud potřeba)

---

## 🎯 Milestones (Updated)

### Milestone 1: Quality Codebase ⭐
**Target:** 2-3 týdny
- ✅ Type hints všude
- ✅ Bare excepts opraveny
- ✅ Duplicitní kód odstraněn
- ✅ Mrtvý kód odstraněn
- **ETA:** 8-12 hodin
- **Status:** Recommended for local CLI tool

### Milestone 2: Robustní Tool
**Target:** 1 měsíc
- ✅ Milestone 1
- ✅ Safety checks
- ✅ Logging framework
- ✅ Config validation
- ✅ Comprehensive tests
- **ETA:** 16-22 hodin
- **Status:** Nice to have

### Milestone 3: Scalable Architecture
**Target:** 2-3 měsíce
- ✅ Milestone 2
- ✅ Modulární struktura
- ✅ DI pattern
- **ETA:** 46-62 hodin
- **Status:** Optional, consider if project grows

---

## 📈 Tracking

### Statistiky
- **Celkový počet úkolů:** 18 (down from 31)
- **✅ Hotové úkoly:** 8 úkolů (44% priority 1 dokončeno!)
- **Vysoká priorita (Code Quality):** 8 úkolů - **6 hotových**, 2 částečně hotové
- **Střední priorita (Safety):** 7 úkolů - **1 hotový**, 6 zbývá
- **Nízká priorita (Architecture):** 3 úkoly - 0 hotových

### Časový odhad (aktualizováno)
- **✅ Rychlé výhry:** ~2 hodiny → **HOTOVO!**
- **⏳ Priority 1 zbývá:** ~4-7 hodin (type hints fáze 2-3, refactoring)
- **Doporučené (Quality + Safety):** 12-17 hodin zbývá (Fáze 1+2)
- **Plný refactoring (Optional):** 42-57 hodin zbývá (všechny fáze)

### Doporučené Pořadí pro Lokální CLI
1. 🔴 **Code Quality** (#1-8) → Údržba, debugging
2. 🟡 **Safety Checks** (#9-15) → Prevence nehod
3. 🟢 **Architecture** (#16-18) → Pouze pokud projekt roste

---

## 📝 Poznámka o Security Issues

**Důležité:** Všechny "security issues" z původního code review jsou **best practices** pro lokální CLI nástroj, NE kritické zranitelnosti.

**Pro lokální CLI nástroj:**
- Path traversal = **Safety check** (prevence nehod)
- Command injection = **Best practice** (low risk)
- Input validation = **Robustness** (ne security)

**Best practices však zůstávají důležité!** Jen nejsou urgentní jako pro web app.

---

**Last Updated:** 2025-11-22 (Progress Update)
**Tool Context:** Local CLI tool, priorities adjusted
**Progress:** ✅ Rychlé výhry dokončeny! 44% Priority 1 hotové (6/8 úkolů)
**Next Review:** Po dokončení zbývajících úkolů Priority 1 (type hints fáze 2-3, refactoring)
