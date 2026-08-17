---
name: coding-guidelines
description: "Use when: applying or checking C++, Java, or Python coding standards; reviewing naming conventions, formatting rules, indentation, comments, or file organization; answering questions about SonarQube rules; verifying exception handling patterns; checking security coding requirements; enforcing code quality standards. Covers: C++ Coding Guidelines v1.4, Java Coding Guidelines v1.4, Python Coding Guidelines v1.4, naming conventions, formatting, Sonar compliance, clean code principles, unit testing practices."
tools: [codereviewer_lens/ask_guideline, codereviewer_lens/explain_rule, codereviewer_lens/list_guidelines]
---

# Coding Guidelines

This skill provides authoritative answers about mandatory coding standards for C++, Java, and Python. It is the **write-time** reference for authoring compliant code and for answering coding-standard questions.

> **Authoritative fallback (complete corpus).** The reference files below are a curated, bounded
> subset. For the **complete or authoritative text of any rule** — especially anything not covered
> here — query the full embedded guideline corpus via `codereviewer_lens/ask_guideline(question,
> language)` (RAG over the full C++/Java/Python coding-guideline PDFs, returning page-cited answers);
> use `explain_rule(rule_id)` to expand a specific SonarQube/tool rule. At **review** time, guideline
> compliance is enforced by the `code-review-lens` skill (the review brain), not here.

> **Version & canonical source.** Pinned to **v1.4**. The **canonical** documents are the PDFs
> embedded in `codereviewer_lens` (`guidelines/<lang>/source/*.pdf`); the reference files here are a
> readable **projection** for authoring. On a version bump, update lens's PDFs **and** these
> references together.

> **SonarQube rules are not a static list.** The guidelines describe standards in prose and reference
> the DBAG SonarQube **quality profile** — they do **not** enumerate every rule ID. The SonarQube
> instance holds **~798 C++, ~2190 Java, ~416 Python** rules — far too many, and too fast-changing, to
> mirror here — so the complete, enforced rule set is the **live quality profile queried by
> `code-review-lens` at review time**. For authoring, browse the authoritative live catalogue at
> **https://sonarp1.deutsche-boerse.de/coding_rules** (filter by language / quality profile), ask
> `codereviewer_lens/ask_guideline` for the prose standard, or `explain_rule(<rule_id>)` to expand a
> specific finding. Do **not** inline or maintain a rule-ID catalogue here.

### Languages: prose guidelines vs SonarQube enforcement

Written DBAG coding-guideline documents exist for **C++, Java, Python** (the reference files below).
But code review is **not limited to those three** — the project's SonarQube quality profiles enforce
**13 languages**, and `code-review-lens` surfaces those findings at review time. For a language with
no prose guideline here, the standard **is** its SonarQube profile (browse `/coding_rules`).

| Language | Quality profile | Active rules¹ |
|---|---|---|
| C | Trading_C_2022_Default_Level | 248 |
| C++ | Trading_C++_2022_Default_Level | 409 |
| Java | Trading_Java_2022_Default_Level | 1341 |
| Python | Trading_Python_2022_Default_Level | 205 |
| JavaScript | Trading_JavaScript_2022_Default_Level | 190 |
| TypeScript | Trading_TypeScript_2025_Default_Level | 257 |
| PL/SQL | Trading 2019 | 115 |
| PHP | Sonar way (built-in) | 196 |
| HTML | Sonar way (built-in) | 53 |
| CSS | Sonar way (built-in) | 27 |
| XML | Sonar way (built-in) | 25 |
| Shell | Sonar way (built-in) | 23 |
| YAML | YAML Analyzer (built-in) | 20 |

¹ Point-in-time counts; the live profiles at `sonarp1.deutsche-boerse.de/coding_rules` are authoritative.

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
