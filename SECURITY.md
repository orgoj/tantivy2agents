# Security Policy

## Supported Versions

| Version | Supported          | Security Status |
| ------- | ------------------ | --------------- |
| 1.0.x   | :white_check_mark: | 4 Critical issues identified |
| < 1.0   | :x:                | Not supported |

## Current Security Status

**Last Security Review:** 2025-11-22

### ⚠️ Known Critical Vulnerabilities

As of the latest code review (2025-11-22), **4 CRITICAL security vulnerabilities** have been identified and documented. See [CODE_REVIEW.md](CODE_REVIEW.md) Section 1 for complete details.

**Status:** 🔴 **NOT PRODUCTION READY** - Critical fixes required

### Summary of Critical Issues

1. **Path Traversal in File Export** (CRITICAL)
   - OWASP: A01:2021 - Broken Access Control
   - Impact: Arbitrary file write
   - Status: ❌ Not fixed
   - Fix Priority: IMMEDIATE

2. **Path Traversal via Glob Patterns** (CRITICAL)
   - OWASP: A03:2021 - Injection
   - Impact: Arbitrary file read
   - Status: ❌ Not fixed
   - Fix Priority: IMMEDIATE

3. **Unsafe Symlink Creation** (HIGH)
   - OWASP: A01:2021 - Broken Access Control
   - Impact: Symlink attacks
   - Status: ❌ Not fixed
   - Fix Priority: HIGH

4. **Unsafe Directory Deletion** (HIGH)
   - OWASP: A01:2021 - Broken Access Control
   - Impact: Arbitrary directory deletion
   - Status: ❌ Not fixed
   - Fix Priority: HIGH

**Full details:** See [CODE_REVIEW.md](CODE_REVIEW.md) Section 1

---

## Reporting a Vulnerability

### Please DO NOT

- ❌ Open a public GitHub issue for security vulnerabilities
- ❌ Discuss vulnerabilities in public forums or social media
- ❌ Exploit vulnerabilities maliciously

### Please DO

1. **Check existing documentation first**
   - Review [CODE_REVIEW.md](CODE_REVIEW.md) - Known vulnerabilities are documented
   - Check [TODO.md](TODO.md) - Security fixes may be planned

2. **If it's a new vulnerability:**
   - Contact the repository maintainers privately
   - Include:
     - Description of the vulnerability
     - Steps to reproduce
     - Potential impact
     - Suggested fix (if any)

3. **Wait for acknowledgment**
   - We aim to acknowledge within 48 hours
   - We will work with you on disclosure timeline

---

## Security Review Process

This project undergoes regular security reviews:

- **Automated:** Static analysis, dependency scanning
- **Manual:** Comprehensive code reviews
- **Documentation:** All findings documented in CODE_REVIEW.md

### Latest Review

**Date:** 2025-11-22
**Method:** Comprehensive parallel agent analysis
**Coverage:** 100% of codebase
**Findings:** 15 security issues total
  - 4 Critical
  - 3 High
  - 7 Medium
  - 1 Low

**Report:** [CODE_REVIEW.md](CODE_REVIEW.md)

---

## Security Best Practices for Users

### Before Using This Tool

⚠️ **WARNING:** This version has known critical security vulnerabilities.

**Recommendations:**

1. **Do NOT use in production** until critical fixes are applied
2. **Do NOT process untrusted input** (file paths, glob patterns)
3. **Do NOT run with elevated privileges**
4. **Use in isolated environment** (container, VM) for testing
5. **Review configuration** before running indexing

### Safe Usage Guidelines

**If you must use the current version:**

1. **Restrict file paths**
   - Only index files within project directory
   - Do not allow user-controlled paths in config

2. **Validate configuration**
   - Review `.tantivi2agents.json` manually
   - Ensure no absolute paths or `..` in patterns

3. **Limit export destinations**
   - Only export to current directory
   - Never use user-controlled output paths

4. **Monitor activity**
   - Review what files are being indexed
   - Check output destinations

5. **Isolate environment**
   - Run in container or VM
   - Restrict file system access
   - Use dedicated user with minimal permissions

---

## Security Checklist for Contributors

When contributing code, ensure:

- [ ] No path traversal vulnerabilities
- [ ] All file paths are validated
- [ ] No command injection risks
- [ ] Input sanitization for user data
- [ ] Secure file permissions (0o700 for sensitive files)
- [ ] No hardcoded secrets or credentials
- [ ] Dependencies are up to date
- [ ] Subprocess calls use list form (not `shell=True`)
- [ ] Error messages don't leak sensitive info
- [ ] File operations check sizes before reading

**Detailed guidelines:** [CONTRIBUTING.md](CONTRIBUTING.md) Security Section

---

## Dependencies Security

### Current Dependencies

```
PyYAML==6.0.2          # ⚠️ Update to 6.0.3 recommended
tantivy==0.24.0        # ✓ No known vulnerabilities
charset-normalizer==3.3.2  # ✓ No known vulnerabilities
```

### Dependency Policy

- **Monitor:** All dependencies for CVEs
- **Update:** Security patches within 7 days
- **Pin:** Exact versions for reproducibility
- **Audit:** Regular `pip-audit` / `safety` scans

### Known Dependency Issues

- **PyYAML 6.0.2:** May have known issues, update to 6.0.3+ recommended
  - Status: ⚠️ Update planned (see TODO.md #21)
  - Priority: MEDIUM
  - Risk: Low (using `safe_load`)

---

## Security Fixes Timeline

### Immediate (Week 1)
- [ ] Fix path traversal in exports (#1)
- [ ] Validate glob patterns (#2)
- [ ] Secure symlink creation (#3)
- [ ] Safe directory deletion (#4)

**ETA for secure release:** 4-6 hours development time

### Short-term (Week 2-3)
- [ ] Command injection fixes (#5, #6)
- [ ] Config validation (#9)
- [ ] Query sanitization (#10)

### Ongoing
- [ ] Dependency updates
- [ ] Regular security audits
- [ ] Automated security scanning

**Full roadmap:** [TODO.md](TODO.md) Section 1

---

## Security Disclosure Policy

### Timeline

1. **Day 0:** Vulnerability reported privately
2. **Day 1-2:** Acknowledgment sent to reporter
3. **Day 3-7:** Vulnerability validated and assessed
4. **Day 7-14:** Fix developed and tested
5. **Day 14:** Security patch released
6. **Day 14+7:** Public disclosure (if coordinated)

### Credit

We will credit security researchers who:
- Report vulnerabilities responsibly
- Follow coordinated disclosure
- Provide helpful details

**Hall of Fame:** (To be added when applicable)

---

## Security Tools

### Recommended Tools for Analysis

```bash
# Dependency vulnerabilities
pip install safety
safety check

pip install pip-audit
pip-audit

# Static analysis
pip install bandit
bandit -r tantivy2agents.py

# Code quality
pip install pylint
pylint tantivy2agents.py
```

### CI/CD Integration

Planned security checks (not yet implemented):
- Automated dependency scanning
- Static security analysis
- Secret scanning
- License compliance

---

## Contact

For security-related matters:

- **Known issues:** See [CODE_REVIEW.md](CODE_REVIEW.md)
- **New vulnerabilities:** Contact maintainers privately (repository maintainer contact)
- **General security questions:** Open issue with `[Security Question]` prefix (for non-vulnerability questions)

---

## Acknowledgments

### Security Review Contributors

- **2025-11-22:** Comprehensive code review by automated security analysis agents
  - 4 parallel agents (Correctness, Security, Best Practices, Documentation)
  - Coverage: 100% of codebase (2,721 lines)
  - Findings: 52 total issues (15 security-related)

---

## Additional Resources

- **OWASP Top 10:** https://owasp.org/www-project-top-ten/
- **Python Security Best Practices:** https://python.readthedocs.io/en/latest/library/security_warnings.html
- **CWE Database:** https://cwe.mitre.org/

---

**Last Updated:** 2025-11-22
**Next Review:** After critical fixes are applied
