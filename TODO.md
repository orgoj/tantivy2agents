TODO

## Code Review Doporučení k Implementaci

### 1. Konzistentní Exception Handling v agent.py

**Problém**: `agent.py` stále používá `print()` a `sys.exit()` místo strukturovaných exceptions.

**Konkrétní případy**:
- `_load_config()`: Silent failure při `json.JSONDecodeError` → zvednout `ConfigError`
- `search_command()`: Index not found → `raise IndexNotFoundError(index_dir=index_dir)`
- `skill_*_command()`: FileNotFoundError skills → `raise FileSystemError(path=skill_path)`
- Obecně: Nahradit všechny `print("Error...")` a `sys.exit(1)` za příslušné `CLIError` subclasses

**Příklad**:
```python
# MÍSTO TOHOTO:
if not os.path.exists(index_dir):
    print("Index not found. Run 'tantivy2agents index' first")
    return

# TOHOTO:
raise IndexNotFoundError(index_dir=index_dir)
```

### 2. Vylepšení Testovací Suite (test_typer_cli.py)

**Problém**: Testy mají slabou izolaci a závisí na sdíleném stavu.

**Úkoly**:
- Přidat `pytest` fixtures s `tmp_path` pro izolované testy
- Použít `monkeypatch` pro mocking `TantivyAgent` v unit testech CLI vrstvy
- Zlepšit assertions (konkrétní hodnoty místo substring checks)

**Příklad**:
```python
@pytest.fixture
def indexed_project(tmp_path):
    """Vytvoří izolovaný projekt s indexem."""
    # Setup files, config, run index
    yield runner, temp_dir
```

**Chybějící coverage**:
- `--output` option pro `search` command
- `--dirs` a `--files` options pro `index` command
- Empty/non-existent index edge cases

### 3. Validace v Typer CLI

**Problém**: Některé validace jsou stále manuální místo deklarativních.

**Úkoly**:
- Vyčistit ruční validation checks, které Typer umí sám
- Auditovat ostatní options/arguments a převést další jednoduché hranice na Typer deklarace

**Příklad**:
```python
# MÍSTO RUČNÍ VALIDACE V TĚLE FUNKCE:
limit: Optional[int] = typer.Option(None, "--limit", "-l", help="Max results")
# ... ruční check v těle funkce

# POUŽÍT DEKLARATIVNÍ VALIDACI, KDE TO JDE:
limit: Optional[int] = typer.Option(None, "--limit", "-l", min=1, max=10000, help="Max results")
```

## Priority

1. **Vysoká**: Konzistentní exception handling (vylepšuje UX pro AI i lidi)
2. **Střední**: Lepší test izolace (robustnější test suite)
3. **Nízká**: Deklarativní validace (code cleanliness, minor improvement)
