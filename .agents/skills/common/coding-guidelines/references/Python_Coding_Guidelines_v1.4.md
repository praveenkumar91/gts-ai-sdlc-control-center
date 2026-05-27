# Coding Guidelines Standards for Python (v1.4)

## Metadata
- **Owner**: Integr., Configur. Mgmt & DevOps Tool (U) Team
- **Author**: Prem Chandra Shekhar
- **Reviewed by**: Olaf Dannenberg
- **Release Date**: 15-10-2025
- **Version**: 1.4

---

## 1. Objective
This document defines Python coding standards to:
- Ensure readability and maintainability
- Enable collaboration across teams
- Align with PEP8 and enterprise standards

Key facts:
- ~80% of software cost is maintenance
- Code is developed by multiple engineers over time

---

## 2. Zen of Python (Key Principles)
- Readability counts
- Explicit > implicit
- Simple > complex
- Errors should never pass silently
- One obvious way to do things

---

## 3. Top 10 Behavioral Commandments
- Ensure readability and maintainability
- Validate inputs (null + range)
- Write secure code
- Consider performance
- Use exceptions properly
- Ensure supportability (logging, naming)
- Maintain consistent style
- Rewrite bad code instead of commenting
- Refactor continuously

---

## 4. Code Layout
### Indentation
- 4 spaces
- No tabs (except legacy consistency)

### Line Length
- Max 180 characters

### Imports
- One per line
- Order:
  1. Standard library
  2. Third-party
  3. Local
- Avoid wildcard imports

### Encoding
- UTF-8 mandatory

---

## 5. Naming Conventions
- Variables/functions: `snake_case`
- Classes: `CapWords`
- Constants: `UPPER_CASE`
- Avoid: `l`, `I`, `O`

### Additional Rules
- Use descriptive, intention-revealing names
- Avoid shadowing built-ins (`list`, `str`)
- Use meaningful, searchable names

---

## 6. Comments & Documentation
- Explain **why**, not what
- Keep comments up to date
- Avoid redundant comments
- Use docstrings (PEP 257)

### Types of Comments
- Block comments
- Inline comments (sparingly)
- Docstrings (mandatory for public APIs)

---

## 7. Python Best Practices
- Use `is` for None checks
- Prefer `def` over lambda assignments
- Use context managers (`with`)
- Use `isinstance()` for type checks
- Avoid global namespace pollution

### Functions
- Raise exceptions instead of returning None
- Use keyword arguments for clarity
- Limit return unpacking to max 3 values

### Classes
- Prefer simple attributes over getters/setters
- Use `@property` when necessary
- Use mixins instead of deep inheritance

---

## 8. Exception Handling
- Never use exceptions for flow control
- Catch specific exceptions only
- Do not swallow exceptions
- Use exception chaining (`raise ... from ...`)

### Best Practices
- Handle exceptions at the correct layer
- Do not expose implementation details
- Document thrown exceptions

---

## 9. Testing
Follow FIRST principle:
- Fast
- Independent
- Repeatable
- Self-validating
- Timely

---

## 10. Code Quality (SonarQube)
- Enforce rules for:
  - Vulnerabilities
  - Bugs
  - Code smells
  - Security hotspots

### Key Rules Examples
- No hardcoded credentials
- No wildcard imports
- Avoid unused variables
- Prevent injection vulnerabilities

---

## 11. Security
- Follow OWASP standards
- Do not hardcode secrets
- Separate config from code
- Enforce secure API usage

---

## 12. Clean Code Principles
- Avoid duplication
- Remove dead code
- Keep methods small
- Ensure consistency
- Prefer abstraction over repetition

---

## 13. Unit Testing Practices
- Test everything that can break
- Focus on boundary conditions
- Keep tests fast and reliable

---

## 14. Key Takeaways
- Follow PEP8 + internal standards
- Write secure, maintainable, readable code
- Enforce quality using automated tools (SonarQube)
- Continuously refactor and improve

---

*This Markdown file is a structured extraction of the original 82-page guideline for practical usage in repositories and developer onboarding.*
