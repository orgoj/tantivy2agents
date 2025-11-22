# Tantivi2Agents Documentation

Welcome to the Tantivi2Agents documentation directory. This guide helps you find the right documentation for your needs.

## 📚 Documentation Structure

### For Users

| Document | Purpose | Audience |
|----------|---------|----------|
| **[README.md](../README.md)** | Quick start, usage guide, CLI reference | End users |
| **[examples/](../examples/)** | Example configurations | Users customizing the tool |
| **[CHANGELOG.md](../CHANGELOG.md)** | Version history, upgrade guides | Users tracking changes |

### For Contributors

| Document | Purpose | Audience |
|----------|---------|----------|
| **[CONTRIBUTING.md](../CONTRIBUTING.md)** | Development workflow, testing, guidelines | Contributors |
| **[.claude/CLAUDE.md](../.claude/CLAUDE.md)** | Strict development rules (REQUIRED reading) | All developers |
| **[CODE_REVIEW.md](../CODE_REVIEW.md)** | Comprehensive code review, architecture insights | Developers, maintainers |
| **[TODO.md](../TODO.md)** | Prioritized task list, roadmap | Developers, maintainers |

### Legal & Licensing

| Document | Purpose |
|----------|---------|
| **[LICENSE](../LICENSE)** | MIT License full text |

---

## 🚀 Quick Start Guide

### I want to...

**...use the tool**
→ Start with [README.md](../README.md)

**...contribute code**
→ Read [CONTRIBUTING.md](../CONTRIBUTING.md) then [.claude/CLAUDE.md](../.claude/CLAUDE.md)

**...understand the codebase**
→ Read [CODE_REVIEW.md](../CODE_REVIEW.md)

**...see what needs to be done**
→ Check [TODO.md](../TODO.md)

**...customize configuration**
→ See [examples/.tantivi2agents.json](../examples/.tantivi2agents.json)

**...know what changed**
→ Read [CHANGELOG.md](../CHANGELOG.md)

---

## 📖 Documentation Overview

### README.md (Main Documentation)
**Comprehensive user guide covering:**
- Installation (automatic and manual)
- Quick start examples
- All CLI commands with detailed examples
- Configuration reference
- Project type detection
- Export formats
- Claude Code integration
- Troubleshooting

**Target audience:** End users, first-time users

---

### CONTRIBUTING.md (Development Guide)
**Development workflow and standards:**
- Code of conduct
- Strict testing requirements (NO manual testing!)
- Development workflow
- Code quality standards
- Pull request process
- Security guidelines

**Target audience:** Contributors, developers

**⚠️ IMPORTANT:** This project has STRICT rules about automated testing only. Read carefully!

---

### .claude/CLAUDE.md (Development Rules)
**NON-NEGOTIABLE development principles:**
- ❌ Absolutely NO manual testing
- ✅ Automated testing ONLY
- 📋 Documentation must be current
- 🔄 Required workflow

**Target audience:** All developers (REQUIRED reading)

**Status:** These rules are enforced and binding

---

### CODE_REVIEW.md (Technical Deep Dive)
**Comprehensive code analysis:**
- Security vulnerabilities (15 issues identified)
- Code correctness problems (10 issues)
- Code quality and architecture (11 issues)
- Python best practices analysis
- Testing gaps and recommendations
- Documentation quality review
- Prioritized remediation plan

**Contents:**
- 🔴 4 Critical security issues
- 🟡 18 High priority issues
- 🟠 25 Medium priority issues
- Statistics and metrics
- Detailed fix recommendations with code examples

**Target audience:** Developers, security reviewers, maintainers

**Last updated:** 2025-11-22

---

### TODO.md (Roadmap & Tasks)
**Prioritized action items:**
- 🚨 7 Critical security fixes (4-6 hours)
- ⚡ 6 High priority code fixes (6-8 hours)
- 🔧 10 Medium priority improvements (12-15 hours)
- 🏗️ 5 Long-term architecture tasks (30-40 hours)
- 🎯 3 Optional enhancements

**Features:**
- Estimated time for each task
- Code examples for fixes
- Milestones and tracking
- Quick wins section

**Target audience:** Developers, project managers, maintainers

**Status:** Active, updated based on code reviews

---

### CHANGELOG.md (Version History)
**Release notes and changes:**
- Version history
- Feature additions
- Bug fixes
- Deprecation notices
- Upgrade guides

**Target audience:** Users, maintainers

**Format:** Keep a Changelog format
**Versioning:** Semantic Versioning (semver)

---

### examples/ (Configuration Examples)

**File:** `.tantivi2agents.json`

Example configuration showing:
- Custom index directories
- Glob patterns (include/exclude)
- Directory-specific patterns
- Schema field weights
- Search settings
- Hook configuration

**Target audience:** Users customizing the tool

---

## 🔒 Security Documentation

Security-related information is spread across documents:

1. **CODE_REVIEW.md Section 1** - Detailed vulnerability analysis
   - 4 Critical vulnerabilities
   - 3 High severity issues
   - 7 Medium severity issues
   - Exploitation scenarios
   - Fix recommendations

2. **TODO.md Section 1** - Security tasks
   - Critical security fixes (#1-7)
   - Implementation details
   - Time estimates

3. **CONTRIBUTING.md Security Section**
   - Reporting security issues
   - Security considerations for contributors
   - Common vulnerability patterns to avoid

**⚠️ Security Status:** 4 critical vulnerabilities identified, fixes required before production deployment.

---

## 📊 Documentation Metrics

**Total documentation:** ~3,000+ lines
- README.md: 711 lines
- CODE_REVIEW.md: 1,200+ lines
- TODO.md: 400+ lines
- CONTRIBUTING.md: 350+ lines
- CHANGELOG.md: 80+ lines
- Other: 200+ lines

**Documentation-to-Code Ratio:** 27.9% (excellent)

**Coverage:**
- ✅ All features documented
- ✅ All CLI commands documented
- ✅ Configuration fully explained
- ✅ Development workflow documented
- ✅ Security issues documented
- ✅ Roadmap available

---

## 🔄 Documentation Maintenance

### When to Update Documentation

**After every code change:**
- [ ] Update README.md if features/commands changed
- [ ] Update CHANGELOG.md with entry
- [ ] Update TODO.md if tasks completed
- [ ] Update CODE_REVIEW.md if architecture changed (major changes)
- [ ] Update CONTRIBUTING.md if workflow changed

### Documentation Review Checklist

- [ ] All examples in README.md work
- [ ] Configuration examples match code defaults
- [ ] CHANGELOG.md has entry for current version
- [ ] TODO.md is up to date
- [ ] No broken links
- [ ] Formatting is correct (Markdown)

---

## 📝 Documentation Style Guide

### Formatting
- Use **Markdown** for all documentation
- Use `code blocks` for code examples
- Use tables for comparisons
- Use emoji sparingly (📚 🚀 ⚠️ ✅ ❌)

### Writing Style
- **Clear and concise** - No fluff
- **Examples over explanation** - Show, don't just tell
- **Active voice** - "Run the command" not "The command should be run"
- **Audience-aware** - Know who you're writing for

### Code Examples
- Always include **working examples**
- Show **expected output**
- Include **error cases** when relevant
- Use **realistic data**

---

## 🎯 Documentation Priority

### High Priority (Always Keep Updated)
1. README.md - User-facing changes
2. CHANGELOG.md - Version tracking
3. TODO.md - Current state of project

### Medium Priority (Update As Needed)
4. CONTRIBUTING.md - When workflow changes
5. CODE_REVIEW.md - After major refactoring
6. examples/ - When defaults change

### Low Priority (Stable)
7. LICENSE - Rarely changes
8. This file (docs/README.md) - Update when structure changes

---

## 🆘 Getting Help

### I can't find what I'm looking for

1. Check the [main README.md](../README.md) first
2. Search across all docs (use grep or IDE search)
3. Check [TODO.md](../TODO.md) - maybe it's a known gap
4. Open an issue with `[Documentation]` prefix

### I found an error in the docs

1. Check if it's already in [TODO.md](../TODO.md)
2. Submit a PR with the fix
3. Follow [CONTRIBUTING.md](../CONTRIBUTING.md) guidelines

### I want to add documentation

1. Read [CONTRIBUTING.md](../CONTRIBUTING.md)
2. Ensure automated tests exist for what you're documenting
3. Update relevant docs (usually README.md + CHANGELOG.md)
4. Submit PR

---

## 📚 External Resources

### Python Resources
- [PEP 8 Style Guide](https://peps.python.org/pep-0008/)
- [Type Hints (PEP 484)](https://peps.python.org/pep-0484/)
- [pytest Documentation](https://docs.pytest.org/)

### Tantivy Resources
- [Tantivy Python Bindings](https://github.com/quickwit-oss/tantivy-py)
- [Tantivy Documentation](https://github.com/quickwit-oss/tantivy)

### Documentation Standards
- [Keep a Changelog](https://keepachangelog.com/)
- [Semantic Versioning](https://semver.org/)
- [Markdown Guide](https://www.markdownguide.org/)

---

**Last Updated:** 2025-11-22
**Maintained by:** Tantivi2Agents Contributors
