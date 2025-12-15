
# Tantivy Agent Development Rules

## 🚨 TESTING & DEVELOPMENT PRINCIPLES

### ABSOLUTELY NO MANUAL TESTING
- ❌ **NEVER** run manual bash commands to test functionality
- ❌ **NEVER** create temporary directories manually for testing
- ❌ **NEVER** verify results by inspecting files manually
- ❌ **NEVER** use `ls`, `cat`, `head` to check test outputs

### ✅ AUTOMATED TESTING ONLY
- ✅ **ALWAYS** create automated Python tests in `tests/` directory
- ✅ **ALWAYS** use `tmp/` directory for test data (in .gitignore)
- ✅ **ALWAYS** run `python run_tests.py` to verify functionality
- ✅ **ALWAYS** make tests repeatable and deterministic

### 🎯 SENIOR DEVELOPER STANDARDS
- **Code once, test forever** - No manual verification after initial implementation
- **Test-driven approach** - Write tests that cover all functionality
- **Clean code** - No duplication, no manual cleanup, no temporary files
- **Professional practices** - All functionality must be verifiable via automated tests

## Tantivy Agent hooks
Note: Hooks are now installed in .claude/settings.json, not here.

## 📋 DOCUMENTATION UPDATES

### README.md MUST BE CURRENT
- After ANY code changes, README.md must be updated IMMEDIATELY
- All new CLI options must be documented with examples
- All new features must have clear usage instructions
- Configuration examples must match actual defaults
- All command examples must be tested and working

### CLAUDE.md RULES ARE BINDING
- These rules apply to ALL changes, no exceptions
- Manual testing is strictly forbidden
- Automated tests are mandatory for all functionality
- Documentation must be kept current at all times

## 🔄 WORKFLOW
1. Implement feature
2. Write/update automated tests
3. Run `mise run test` - ALL tests must pass
4. **Bump version** in pyproject.toml AND __init__.py
5. Run `mise run pre-commit` - formatting and linting
6. Update README.md with new functionality
7. Commit changes
8. NEVER manually verify or test anything

## ⚠️ PROJECT-SPECIFIC RULES

### Build System
- **NO Makefile** - use `mise run [task]` for all operations
- Available tasks: `mise run test`, `mise run pre-commit`, `mise run install`
- **NEVER assume** build tools exist - check mise.toml first

### Tantivy API Patterns
- **Document access**: Use `doc[key]` NOT `doc.get(key)` - Tantivy Document has no `.get()` method
- **Missing fields**: `doc[key]` returns `[]` for missing fields, NOT KeyError
- **Schema iteration**: Schema is NOT iterable - use `parse_query(query, None)` to search all fields
- **Backward compatibility**: Always handle missing fields gracefully (check if list is empty)
