# Security Policy

## Tool Context

**Tantivi2Agents** je **lokální CLI nástroj** určený pro použití v izolovaném prostředí. Není určen pro:
- ❌ Webové aplikace
- ❌ Síťové služby
- ❌ Multi-user prostředí
- ❌ Zpracování nedůvěryhodných vstupů

**Typické použití:** Vývojář indexuje vlastní projekty na svém lokálním počítači.

**Důsledky pro bezpečnost:**
- ✅ Riziko vzdálených útoků: **ŽÁDNÉ** (není vystaveno síti)
- ✅ Riziko malicious input: **NÍZKÉ** (uživatel kontroluje vstupy)
- ⚠️ Riziko nehod: **STŘEDNÍ** (chybná konfigurace může poškodit soubory)

---

## Supported Versions

| Version | Supported          | Security Status |
| ------- | ------------------ | --------------- |
| 1.0.x   | :white_check_mark: | Known issues documented (low risk for local use) |
| < 1.0   | :x:                | Not supported |

## Current Security Status

**Last Security Review:** 2025-11-22
**Context:** Local CLI tool, isolated environment

### 📝 Known Security Issues (Best Practices)

Následující problémy byly identifikovány během code review. Pro **lokální CLI nástroj** představují **nízké bezpečnostní riziko**, ale jejich oprava zlepší **robustnost a prevenci chyb**.

**Status:** ✅ **VHODNÉ PRO LOKÁLNÍ POUŽITÍ** - Issues dokumentovány jako best practices

---

### 1. Path Validation Issues

**Kategorie:** Input Validation
**Risk Level pro lokální CLI:** 🟡 LOW → MEDIUM (prevence nehod)
**Risk Level pro web app:** 🔴 CRITICAL

#### 1.1 Chybějící validace výstupních cest
**Lokace:** `tantivy2agents.py:817, 830, 865`
**OWASP:** A01:2021 - Broken Access Control

**Problém:**
```python
if output_file:
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(export_data, f, indent=2, ensure_ascii=False)
```

**Scénář nehody (ne útoku):**
```bash
# Omylem přepíše důležitý soubor
python tantivy2agents.py search "test" --output "../important-data.json"

# Typo v cestě
python tantivy2agents.py search "test" --output "/etc/passwd"  # Selže na permissions, ale...
```

**Doporučená oprava (best practice):**
```python
def _validate_output_path(self, output_file):
    """Prevence náhodného přepsání souborů mimo projekt"""
    abs_path = os.path.abspath(output_file)
    current_dir = os.path.abspath(os.getcwd())

    if not abs_path.startswith(current_dir):
        print(f"⚠️  Warning: Output path outside current directory: {output_file}")
        response = input("Continue? (y/N): ")
        if response.lower() != 'y':
            raise ValueError("Output cancelled by user")

    return abs_path
```

**Priorita:** 🟡 MEDIUM - Prevence nehod, ne bezpečnostní riziko

---

#### 1.2 Chybějící validace glob patterns
**Lokace:** `tantivy2agents.py:290, 293, 307, 309`

**Problém:** Konfigurace může obsahovat absolutní cesty nebo `..`

**Scénář nehody:**
```json
{
  "index_dirs": [
    "/etc/**",  // Omylem
    "../../../sensitive-data/**"  // Typo
  ]
}
```

**Doporučená oprava (safety check):**
```python
def _validate_path_pattern(self, pattern):
    """Varování při podezřelých patterns"""
    if os.path.isabs(pattern):
        print(f"⚠️  Warning: Absolute path in config: {pattern}")
        print("   This will index files outside project directory.")
        response = input("Continue? (y/N): ")
        if response.lower() != 'y':
            raise ValueError("Indexing cancelled by user")

    if ".." in pattern:
        print(f"⚠️  Warning: Parent directory traversal: {pattern}")
        # ... similar confirmation
```

**Priorita:** 🟡 MEDIUM - User safety, ne security

---

#### 1.3 Nebezpečné mazání adresářů
**Lokace:** `tantivy2agents.py:684, 936, 1178`

**Problém:** `shutil.rmtree()` bez validace cesty

**Scénář nehody:**
```bash
# Symlink accident
ln -s ~/important-data .tantivy-data
python tantivy2agents.py clear  # Smaže important-data!
```

**Doporučená oprava (safety):**
```python
def _safe_rmtree(self, path):
    """Prevence náhodného smazání důležitých dat"""
    abs_path = os.path.abspath(path)

    # Check it's within project
    if not abs_path.startswith(os.path.abspath(self.project_root)):
        raise ValueError(f"Cannot delete outside project: {path}")

    # Check it's not a symlink
    if os.path.islink(path):
        print(f"⚠️  Warning: {path} is a symlink!")
        print(f"   Target: {os.readlink(path)}")
        response = input("Delete symlink (not target)? (y/N): ")
        if response.lower() == 'y':
            os.unlink(path)  # Delete symlink only
            return
        raise ValueError("Delete cancelled")

    shutil.rmtree(abs_path)
```

**Priorita:** 🟢 LOW-MEDIUM - Nice to have safety check

---

### 2. Code Quality Issues (Higher Priority)

Tyto problémy mají **vyšší prioritu** než security pro lokální CLI nástroj:

#### 2.1 Bare except klauzule (16 výskytů)
**Priorita:** 🔴 HIGH
**Dopad:** Ztížené debugování, skryté chyby

```python
# Špatně - potlačuje i KeyboardInterrupt
except:
    pass

# Dobře
except (IOError, ValueError) as e:
    logging.debug(f"Expected error: {e}")
```

#### 2.2 Chybějící type hints
**Priorita:** 🔴 HIGH
**Dopad:** Horší IDE podpora, více bugů

#### 2.3 Duplicitní kód
**Priorita:** 🟡 MEDIUM
**Dopad:** Údržba, konzistence

---

## Security Best Practices for Local CLI Tools

### Pro Uživatele

**Bezpečné použití:**
- ✅ Kontroluj konfiguraci před indexováním
- ✅ Dávej pozor na cesty v `--output` flagů
- ✅ Nepoužívej konfigurace z nedůvěryhodných zdrojů
- ✅ Zálohuj data před použitím `clear` příkazu

**Není potřeba:**
- ❌ Spouštět v izolovaném kontejneru (overkill)
- ❌ Omezovat file system permissions (běží jako ty)
- ❌ Validovat každý vstup (kontroluješ ho sám)

### Pro Vývojáře

**Při přidávání features:**
- ✅ Přidej user confirmation pro destruktivní operace
- ✅ Validuj cesty jako prevenci nehod (ne útoků)
- ✅ Loguj co nástroj dělá
- ✅ Používej type hints a proper error handling

**Není potřeba:**
- ❌ Sanitizace proti injection útokům
- ❌ Rate limiting, CSRF protection, atd.
- ❌ Security audit každé změny

---

## Reporting Issues

### Bezpečnostní problémy

Pro lokální CLI nástroj jsou "security issues" většinou **quality/robustness issues**.

**Pokud najdeš problém:**
1. Check [CODE_REVIEW.md](CODE_REVIEW.md) - může být již dokumentován
2. Check [TODO.md](TODO.md) - může být naplánována oprava
3. Otevři běžný GitHub issue (není potřeba private disclosure)

**Kdy použít private disclosure:**
- Jen pokud problém umožňuje **skutečný útok** (nepravděpodobné pro local CLI)
- Kontaktuj maintainera přímo

### Quality/Robustness problémy

Standardní GitHub issue process:
- Otevři issue s popisem
- Ideálně s reproducible example
- Navrhni fix (pokud máš nápad)

---

## Known Issues Summary

**Dokumentované v CODE_REVIEW.md:**

| Kategorie | Count | Priorita pro Local CLI |
|-----------|-------|----------------------|
| **Path validation** | 4 | 🟡 MEDIUM (safety) |
| **Code quality** | 10 | 🔴 HIGH |
| **Python best practices** | 5 | 🔴 HIGH |
| **Architecture** | 5 | 🟡 MEDIUM |
| **Testing gaps** | 4 | 🟡 MEDIUM |

**Doporučené pořadí:**
1. 🔴 HIGH: Code quality (type hints, bare excepts, duplicity)
2. 🟡 MEDIUM: Path validation (safety checks, confirmations)
3. 🟡 MEDIUM: Architecture refactoring
4. 🟢 LOW: Advanced features

---

## Dependencies Security

```
PyYAML==6.0.2          # ⚠️ Update to 6.0.3 recommended
tantivy==0.24.0        # ✓ No known vulnerabilities
charset-normalizer==3.3.2  # ✓ No known vulnerabilities
```

**Doporučení:**
- Aktualizovat PyYAML (dobré praktiky)
- Pravidelně spouštět `pip-audit` nebo `safety check`

---

## Changelog of Security Status

### 2025-11-22
- **Initial security review** provedena
- **Context clarified:** Lokální CLI nástroj, ne web aplikace
- **Priority adjusted:** Best practices > Security for local use
- Všechny findings dokumentovány v CODE_REVIEW.md
- Roadmap v TODO.md

---

## Contact

Pro jakékoli otázky:
- **Quality/robustness issues:** GitHub issues
- **Feature requests:** GitHub issues
- **Questions:** GitHub discussions nebo issues s `[Question]` prefix

---

## Poznámka o Severity Ratings

**Důležité:** Severity ratings v CODE_REVIEW.md jsou založeny na **web application context**.

**Pro lokální CLI nástroj:**
- "CRITICAL" → "MEDIUM" (safety, ne security)
- "HIGH" → "LOW-MEDIUM" (best practices)
- "MEDIUM" → "LOW" (nice to have)

**Best practices však zůstávají VYSOKÁ PRIORITA** pro kvalitu kódu!

---

**Last Updated:** 2025-11-22
**Tool Context:** Local CLI tool for isolated environment use
**Security Model:** User controls all inputs, no remote attack surface
