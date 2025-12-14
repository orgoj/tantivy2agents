# Contributing to Tantivi2Agents

Thank you for your interest in contributing to Tantivi2Agents! This document provides guidelines and instructions for contributing to the project.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Development Principles](#development-principles)
- [Getting Started](#getting-started)
- [Development Workflow](#development-workflow)
- [Testing Requirements](#testing-requirements)
- [Code Quality Standards](#code-quality-standards)
- [Pull Request Process](#pull-request-process)
- [Security](#security)

---

## Code of Conduct

This project follows standard open-source collaboration practices:
- Be respectful and constructive in all interactions
- Focus on technical merit and code quality
- Help maintain a welcoming environment for all contributors

---

## Development Principles

This project follows **STRICT development rules** documented in `.claude/CLAUDE.md`. These rules are **NON-NEGOTIABLE**:

### 🚨 ABSOLUTELY NO MANUAL TESTING
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

### 📋 DOCUMENTATION UPDATES
- After ANY code changes, README.md must be updated IMMEDIATELY
- All new CLI options must be documented with examples
- All new features must have clear usage instructions
- Configuration examples must match actual defaults
- All command examples must be tested and working

---

## Getting Started

### Prerequisites

- Python 3.8 or higher
- Git
- Virtual environment (recommended)

### Initial Setup

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd tantivy2agents
   ```

2. **Create virtual environment**
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Run tests to verify setup**
   ```bash
   python run_tests.py
   ```

   **Expected output:** All tests should pass ✅

---

## Development Workflow

### 🔄 Standard Workflow

1. **Implement feature**
   - Write production code
   - Follow Python best practices (PEP 8)
   - Add type hints to all new functions
   - Use meaningful variable and function names

2. **Write/update automated tests**
   - Create test in appropriate file in `tests/`
   - Test both success and error cases
   - Ensure tests are isolated and repeatable
   - Use `tmp_path` fixture for file operations

3. **Run test suite**
   ```bash
   python run_tests.py
   ```
   - **ALL tests must pass** ✅
   - Fix any failing tests before proceeding

4. **Update README.md**
   - Document new features with examples
   - Update CLI options section
   - Add configuration examples if needed
   - Verify all examples work

5. **Commit changes**
   ```bash
   git add .
   git commit -m "Description of changes"
   ```

6. **NEVER manually verify or test anything**
   - If functionality works in automated tests, it works ✅
   - Manual testing is forbidden per project rules

---

## Testing Requirements

### Test Organization

```
tests/
├── test_basic.py          # Core functionality tests
├── test_install.py        # Installation and setup tests
├── test_encoding.py       # Encoding detection tests
└── conftest.py           # Shared fixtures (add if needed)
```

### Writing Good Tests

**Example test structure:**
```python
def test_feature_name(tmp_path):
    """Test description explaining what is being tested"""
    # Arrange - Set up test data
    test_file = tmp_path / "test.txt"
    test_file.write_text("test content")

    # Act - Perform the action
    result = function_under_test(test_file)

    # Assert - Verify the result
    assert result == expected_value
```

### Test Requirements

- ✅ All tests must be **deterministic** (same input → same output)
- ✅ Use `tmp_path` fixture for file operations (automatically cleaned up)
- ✅ Test both **success and error cases**
- ✅ Include **edge cases** (empty input, large files, special characters)
- ✅ Tests must **not depend on external state** (network, existing files)
- ✅ Each test should be **independent** (can run in any order)

### Running Tests

```bash
# Run all tests
python run_tests.py

# Run specific test file
python -m pytest tests/test_basic.py -v

# Run specific test
python -m pytest tests/test_basic.py::test_indexing -v

# Run with coverage report
python -m pytest --cov=tantivy2agents tests/
```

---

## Code Quality Standards

### Python Style

- **PEP 8 compliance** - Use standard Python style guide
- **Line length**: Maximum 120 characters
- **Imports**: Group in order (stdlib, third-party, local)
- **Quotes**: Consistent use of double quotes `"` for strings
- **Type hints**: Required for all new functions

### Type Hints Example

```python
from typing import Optional, List, Dict, Any

def process_files(file_paths: List[str],
                 limit: Optional[int] = None) -> Dict[str, Any]:
    """Process files and return results"""
    results: Dict[str, Any] = {}
    # Implementation
    return results
```

### Code Organization

- **Single Responsibility**: Each function/method does one thing
- **DRY Principle**: Don't Repeat Yourself
- **Meaningful Names**: Variables and functions have descriptive names
- **Comments**: Explain *why*, not *what* (code should be self-explanatory)
- **Docstrings**: All public functions must have docstrings

### Error Handling

```python
# ❌ DON'T - Bare except
try:
    operation()
except:
    pass

# ✅ DO - Specific exceptions with logging
try:
    operation()
except (FileNotFoundError, PermissionError) as e:
    logging.error(f"Operation failed: {e}")
    raise
```

---

## Pull Request Process

### Before Submitting PR

1. **Run all tests** - `python run_tests.py` must pass ✅
2. **Update documentation** - README.md reflects all changes
3. **Add changelog entry** - Update CHANGELOG.md
4. **Check code quality** - Follow style guidelines
5. **Security check** - Review CODE_REVIEW.md for common issues

### PR Checklist

- [ ] All automated tests pass
- [ ] New features have tests
- [ ] README.md updated with examples
- [ ] CHANGELOG.md updated
- [ ] No manual testing performed (automated only)
- [ ] Type hints added to new functions
- [ ] Code follows PEP 8 style guide
- [ ] No security vulnerabilities introduced

### PR Description Template

```markdown
## Description
Brief description of changes

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Breaking change
- [ ] Documentation update

## Testing
- [ ] All automated tests pass
- [ ] New tests added for new functionality

## Documentation
- [ ] README.md updated
- [ ] CHANGELOG.md updated
- [ ] Docstrings added/updated

## Checklist
- [ ] Follows project development principles (.claude/CLAUDE.md)
- [ ] No manual testing performed
- [ ] Code has type hints
- [ ] Security considerations reviewed
```

---

## Security

### Reporting Security Issues

If you discover a security vulnerability:

1. **DO NOT** open a public issue
2. Review `CODE_REVIEW.md` for known security issues
3. Check if the issue is already documented in `TODO.md`
4. Contact maintainers privately (via repository maintainer contact)

### Security Considerations

When contributing code, be aware of:

- **Path Traversal**: Validate all file paths
- **Command Injection**: Never use `shell=True` in subprocess
- **Input Validation**: Sanitize all user inputs
- **File Operations**: Check file sizes before reading
- **Permissions**: Use restrictive file permissions (0o700)

See `CODE_REVIEW.md` Section 1 for detailed security guidelines.

---

## Getting Help

- **Documentation**: Check README.md first
- **Code Review**: See CODE_REVIEW.md for architecture insights
- **TODOs**: Check TODO.md for known issues and planned improvements
- **Development Rules**: Read .claude/CLAUDE.md for strict requirements

---

## Project Structure

```
tantivy2agents/
├── tantivy2agents.py       # Main application (monolithic, to be refactored)
├── tests/                  # Automated test suite
│   ├── test_basic.py
│   ├── test_install.py
│   └── test_encoding.py
├── examples/               # Example configurations
│   └── .tantivy2agents.json
├── .claude/               # Development rules
│   ├── CLAUDE.md
│   └── settings.json
├── requirements.txt       # Python dependencies
├── run_tests.py          # Test runner
├── README.md             # User documentation
├── CODE_REVIEW.md        # Comprehensive code review
├── TODO.md               # Prioritized tasks
├── CHANGELOG.md          # Version history
├── CONTRIBUTING.md       # This file
└── LICENSE               # MIT License
```

---

## Development Commands

```bash
# Create feature branch
git checkout -b feature/your-feature-name

# Run tests (REQUIRED before commit)
python run_tests.py

# Check code style
python -m pylint tantivy2agents.py

# Run specific test
python -m pytest tests/test_basic.py::test_indexing -v

# Commit changes
git add .
git commit -m "Add feature: description"

# Push to your fork
git push origin feature/your-feature-name
```

---

## License

By contributing to Tantivi2Agents, you agree that your contributions will be licensed under the MIT License.

---

## Questions?

- Check existing documentation first
- Review closed issues for similar questions
- Open a new issue with `[Question]` prefix

---

**Remember:** This project has STRICT testing requirements. All functionality must be verified through automated tests, not manual testing. This is non-negotiable.

Thank you for contributing! 🚀
