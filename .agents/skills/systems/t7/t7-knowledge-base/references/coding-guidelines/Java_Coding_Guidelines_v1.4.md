# Java Coding Guidelines v1.4 (Full Markdown)

> Converted from original Deutsche Börse PDF (structured, cleaned, Markdown-ready).

---

## 1. Objective

Defines Java coding standards to ensure:
- Readability
- Maintainability
- Security
- Consistency

Key facts:
- ~80% lifecycle cost is maintenance
- Code is maintained by multiple developers

Sources include:
- Oracle Java Specs
- Google Java Style Guide
- Clean Code / Effective Java
- SonarQube standards

---

## 2. Guiding Principles

1. Ensure readability and maintainability
2. Defensive coding (null & range validation)
3. Security-first design
4. Performance awareness
5. Proper exception usage
6. Code supportability (logging)
7. Consistency
8. Rewrite bad code instead of commenting
9. Continuous refactoring
10. Concurrency awareness

---

## 3. Formatting

- 4 spaces indentation (no tabs)
- Max line length: 180
- Use blank lines for separation

---

## 4. Naming

- Classes: PascalCase
- Methods: camelCase
- Constants: UPPER_CASE
- Packages: lowercase

Principles:
- Intention revealing
- Pronounceable
- Searchable

---

## 5. Declarations

- One declaration per line
- Use smallest scope

---

## 6. Comments

- Explain **why**, not **how**
- Avoid outdated comments
- Use doc comments for APIs

---

## 7. File Organization

- Header
- Package
- Imports
- Class

One public class per file

---

## 8. Functions & Classes

- Small
- Single responsibility
- High cohesion
- Avoid side effects

---

## 9. Statements

- One statement per line
- Always use braces

---

## 10. Exception Handling

- Checked → recoverable
- Runtime → programming errors
- Never swallow exceptions
- Always log errors

---

## 11. Code Smells

Examples:
- Dead code
- Duplication
- Magic numbers
- Feature envy

---

## 12. SonarQube

Categories:
- Vulnerabilities
- Bugs
- Security hotspots
- Code smells

Profiles:
- Light
- Default
- Stringent

---

## 13. Security

- Follow OWASP Top 10
- Avoid hardcoded secrets
- Secure APIs

---

## Appendix (Important)

The original document contains:
- 800+ Sonar rules
- Extensive rule tables

➡️ These are intentionally omitted to keep Markdown usable.

Refer to:
https://rules.sonarsource.com/java

---

## Summary

- Clean code
- Secure systems
- Maintainable architecture

---

