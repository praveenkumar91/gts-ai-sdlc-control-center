---
name: coding-guidelines
description: "Use when: applying or checking C++, Java, or Python coding standards; reviewing naming conventions, formatting rules, indentation, comments, or file organization; answering questions about SonarQube rules; verifying exception handling patterns; checking security coding requirements; enforcing code quality standards. Covers: C++ Coding Guidelines v1.4, Java Coding Guidelines v1.4, Python Coding Guidelines v1.4, naming conventions, formatting, Sonar compliance, clean code principles, unit testing practices."
---

# Coding Guidelines

This skill provides authoritative answers about mandatory coding standards for C++, Java, and Python.

## References

- [C++ Coding Guidelines v1.4](./references/C++_Coding_Guidelines_v1.4.md) — C++ standards: naming, formatting, classes, templates, resource management, Sonar rules
- [Java Coding Guidelines v1.4](./references/Java_Coding_Guidelines_v1.4.md) — Java standards: naming, formatting, declarations, exception handling, SonarQube rules
- [Python Coding Guidelines v1.4](./references/Python_Coding_Guidelines_v1.4.md) — Python standards: PEP 8, naming, code layout, exception handling, testing, Sonar rules

## When to Use

- Checking whether a piece of code follows the mandatory coding standards
- Looking up the correct naming convention for a class, function, variable, or file
- Finding the required formatting or indentation rule for a language
- Determining how exception handling must be structured
- Identifying SonarQube rules that apply to a construct
- Verifying security coding requirements (input validation, resource cleanup, etc.)
- Applying unit testing practices and coverage expectations

## Procedure

### Step 1 — Identify Language and Topic

Determine:
- **Language**: C++, Java, or Python
- **Topic**: naming, formatting, comments, functions/classes, exceptions, Sonar rules, security, testing, or general principles

### Step 2 — Load the Correct Guideline

| Language | Reference file |
|---|---|
| C++ | [C++ Coding Guidelines v1.4](./references/C++_Coding_Guidelines_v1.4.md) |
| Java | [Java Coding Guidelines v1.4](./references/Java_Coding_Guidelines_v1.4.md) |
| Python | [Python Coding Guidelines v1.4](./references/Python_Coding_Guidelines_v1.4.md) |

### Step 3 — Navigate to the Relevant Section

Use the section map below to jump directly to the right part of the guideline:

**C++ sections**: Objective · Guiding Principles · Code Layout & Indentation · Naming Conventions · Comments · Functions · Classes/Constructors/Containers · Interfaces · Enumerations · Resource Management · Expressions & Statements · Performance · Templates · Source Files · Error Handling · Sonar Rules

**Java sections**: Objective · Guiding Principles · Formatting · Naming · Declarations · Comments · File Organization · Functions & Classes · Statements · Exception Handling · Code Smells · SonarQube · Security · Appendix · Summary

**Python sections**: Objective · Zen of Python · Top 10 Commandments · Code Layout · Naming Conventions · Comments & Documentation · Best Practices · Exception Handling · Testing · Code Quality (SonarQube) · Security · Clean Code Principles · Unit Testing Practices · Key Takeaways

### Step 4 — Apply or Report the Rule

- State the rule exactly as written in the guideline
- Include any provided code examples (compliant and non-compliant)
- Note any exceptions or conditions documented in the guideline
- Cite the section name and guideline version

### Step 5 — Validate Against the Code (if reviewing)

When reviewing code for guideline compliance:
1. List each violation found with the rule reference
2. Provide the corrected version of the code
3. Explain why the original violated the rule

## Output Format (when returning findings)

```
**Language**: <C++ | Java | Python>
**Guideline version**: v1.4
**Section**: <section name>
**Rule**: <exact rule text>
**Compliant example**: <code snippet if available>
**Finding** (if reviewing code): <what violates the rule and the fix>
```
