# C++ Coding Guidelines (v1.4)

**Owner:** Integr., Configur.Mgmt&Dev.OpsTool (U) Team, Deutsche Börse AG  \
**Author:** Prem Chandra Shekhar  \
**Reviewed by:** Olaf Dannenberg  \
**Release Date:** 15-10-2025  \
**Status:** Yearly Reviewed & Updated

---

## Table of Contents

- [C++ Coding Guidelines (v1.4)](#c-coding-guidelines-v14)
  - [Table of Contents](#table-of-contents)
  - [1. Document Objective and Sources of Coding Standards](#1-document-objective-and-sources-of-coding-standards)
  - [2. Guiding Principles: Top 10 Behavioral Commandments](#2-guiding-principles-top-10-behavioral-commandments)
  - [3. Code Layout and Indentation](#3-code-layout-and-indentation)
    - [3.1 Code Layout](#31-code-layout)
    - [3.2 Formatting and Indentation](#32-formatting-and-indentation)
  - [4. Naming Conventions](#4-naming-conventions)
    - [4.1 Naming and Layout Best Practices](#41-naming-and-layout-best-practices)
  - [5. Comments](#5-comments)
  - [6. Functions](#6-functions)
  - [7. Classes, Constructors, Containers, and Hierarchies](#7-classes-constructors-containers-and-hierarchies)
  - [8. Interfaces](#8-interfaces)
  - [9. Enumerations](#9-enumerations)
  - [10. Resource Management](#10-resource-management)
  - [11. Expressions and Statements](#11-expressions-and-statements)
  - [12. Performance](#12-performance)
  - [13. Templates and Generic Programming](#13-templates-and-generic-programming)
  - [14. Source Files](#14-source-files)
  - [15. The Standard Library](#15-the-standard-library)
  - [16. Error and Exception Handling](#16-error-and-exception-handling)
  - [17. C++ Sonar Code Quality Checks Standards](#17-c-sonar-code-quality-checks-standards)
  - [18. Appendix](#18-appendix)
    - [18.1 Sources of Code Smells and Bugs](#181-sources-of-code-smells-and-bugs)
    - [18.2 Unit Tests](#182-unit-tests)
    - [18.3 Effectiveness in Programming C++](#183-effectiveness-in-programming-c)
    - [18.4 Secure Software Development Standard (Synopsis)](#184-secure-software-development-standard-synopsis)

---

## 1. Document Objective and Sources of Coding Standards

The purpose of this guideline is to introduce and explain rules recommended for C++ software development. It is reviewed yearly and is intended to ensure a common style and high code quality.

**Key Sources:**

- [C++ Core Guidelines](https://isocpp.github.io/CppCoreGuidelines/CppCoreGuidelines)
- [Google C++ Style Guide](https://google.github.io/styleguide/cppguide.html)
- *C++ Coding Standards: 101 Rules, Guidelines, and Best Practices* (Herb Sutter, Andrei Alexandrescu)
- *Clean Code* and *Clean Architecture* (Robert C. Martin)
- *The Pragmatic Programmer* (David Thomas, Andrew Hunt)

**SonarQube Integration:**  \
SonarQube is used for automated code quality checks.

---

## 2. Guiding Principles: Top 10 Behavioral Commandments

1. **Enhance code readability and maintainability.**
2. **Code defensively:** Validate all input parameters.
3. **Think about security:** Defend code from vulnerabilities.
4. **Think about performance:** Consider real datasets and bottlenecks.
5. **Use exceptions correctly:** Handle exceptions at the right level.
6. **Consider supportability:** Use logging and clear comments.
7. **Maintain consistent code style and structure.**
8. **Don’t comment bad code—rewrite it.**
9. **Think refactoring:** Improve internal structure without changing behavior.
10. **Concurrency:** Use concurrency to decouple what gets done from when.

**Additional Best Practices:**

- Express ideas directly in code.
- Prefer compile-time checking.
- Don’t leak resources.
- Prefer immutable data.
- Use supporting tools and libraries.

---

## 3. Code Layout and Indentation

### 3.1 Code Layout

- Follow GNU coding standard layout for C, extended to C++.
- Use **4 spaces** for indentation, **no tabs**.
- Avoid lines longer than **180 columns**.
- Surround operators and commas with spaces.
- Method and function definitions should have braces on their own lines.

**Examples:**

```cpp
a = (b + c) * d; // Good
while (true) { /* ... */ }
doSomething(a, b, c, d);
for (i = 0; i < 10; i++) { /* ... */ }
```

### 3.2 Formatting and Indentation

- Each line should be at most 180 characters.
- Use UTF-8 for non-ASCII characters.
- Use only spaces for indentation.
- Lambda expressions: Format like functions.
- Floating-point literals: Always use a radix point (e.g., `1.0`).
- Function calls: Arguments aligned if wrapped.
- Braced initializer lists: Format like function calls.
- Conditionals: Space after `if`, no space inside parentheses.
- Loops and switch: Use braces; annotate fall-through.
- Pointer/reference: No spaces around `.` or `->`; use consistent spacing in declarations.
- Boolean expressions: Break lines consistently.
- Return values: Avoid unnecessary parentheses.
- Variable initialization: Always initialize before use.
- Preprocessor directives: `#` must be the first character on the line.
- Class format: `public`, `protected`, `private` order.
- Constructor initializer lists: Align members.
- Namespace formatting: No extra indentation inside namespaces.
- Whitespace: No trailing whitespace; minimize vertical whitespace.

---

## 4. Naming Conventions

- **Header files:** `.hxx`  \
  **Source files:** `.cxx`
- **Classes:** PascalCase (`MyClass`)
- **Variables:** camelCase (`myVariable`)
- **Constants:** ALL_CAPS with underscores (`MAX_ITERATIONS`)
- **Methods:** PascalCase, start with a verb (`ComputeTotalWidth`)
- **Namespaces:** lowercase
- **Template types:** Single uppercase letter or explicit concept name
- **Abbreviations:** Avoid ALL CAPS in identifiers
- **Boolean variables:** Prefix with `is`, `has`, `need`
- **Collections:** Use plural names
- **Avoid:** Hungarian notation, negated boolean names, type encoding in names

### 4.1 Naming and Layout Best Practices

- Don’t say in comments what can be stated in code.
- State intent in comments.
- Keep comments crisp and professional.
- Avoid encoding type information in names.
- Name length should match scope.
- Use ALL_CAPS for macros only.
- Prefer CamelCase/PascalCase over underscores where applicable.
- Make literals readable with digit separators.
- Declare **one name per declaration**.

---

## 5. Comments

- Comments should explain **why**, not **how**.
- Use block comments for overviews, line comments for specifics.
- Use `TODO`, `FIXME`, and similar keywords for issues.
- Prefer `//` and be consistent.
- File/class/function/variable comments should explain purpose, usage, and invariants.
- Avoid redundant comments and commented-out code.

---

## 6. Functions

- Prefer return values over output parameters.
- Write short, focused functions.
- Use function overloading only when it improves readability.
- Default arguments allowed on non-virtual functions.
- Use trailing return type syntax only when necessary.
- Follow best practices for parameter passing and return semantics.
- Prefer pure functions and `constexpr`/`inline` where appropriate.

---

## 7. Classes, Constructors, Containers, and Hierarchies

- Organize related data into structs/classes.
- Prefer concrete types over class hierarchies.
- Define constructors, assignments, and destructors as needed.
- Follow the **Rule of Zero/Three/Five**.
- Containers should follow STL conventions.
- Use class hierarchies only for inherently hierarchical concepts.
- Avoid trivial getters/setters and unnecessary virtual functions.

---

## 8. Interfaces

- Make interfaces explicit, precisely and strongly typed.
- Avoid non-const globals and singletons.
- State preconditions and postconditions.
- Use exceptions only for unrecoverable errors.
- Prefer empty abstract classes as interfaces.

---

## 9. Enumerations

- Prefer enums over macros.
- Use `enum class` over plain enums.
- Avoid ALL_CAPS for enumerators.
- Specify underlying types and values only when necessary.

---

## 10. Resource Management

- Use RAII for resource management.
- Prefer scoped objects; avoid explicit `new`/`delete`.
- Use smart pointers (`std::unique_ptr`, `std::shared_ptr`) for ownership.
- Avoid non-const global variables.
- Always release resources in destructors.

---

## 11. Expressions and Statements

- Prefer the standard library and suitable abstractions.
- Keep scopes small, names meaningful, and always initialize variables.
- Avoid complicated expressions, casts, and magic constants.
- Prefer range-for loops and `switch` statements where appropriate.
- Avoid `goto`; minimize `break`/`continue`; handle arithmetic carefully.

---

## 12. Performance

- Don’t optimize prematurely.
- Measure before optimizing.
- Minimize allocations; use compact data structures; access memory predictably.

---

## 13. Templates and Generic Programming

- Use templates to raise abstraction and express algorithms/containers.
- Specify concepts/constraints for template arguments.
- Prefer standard concepts and template facilities.
- Avoid over-parameterization and non-generic code.

---

## 14. Source Files

- Use header files for declarations, source files for definitions.
- Use include guards in all headers.
- Avoid cyclic dependencies.
- Avoid global `using namespace` in headers.

---

## 15. The Standard Library

- Prefer the standard library to other libraries.
- Use containers, strings, iostream, regex, chrono, and other standard components.
- Do not add non-standard entities to the `std` namespace.

---

## 16. Error and Exception Handling

- Use exceptions for error handling only.
- Use RAII to prevent leaks.
- Never throw while owning an object.
- Use user-defined types for exceptions.
- Catch exceptions by reference.
- Destructors, deallocation, and swap must never fail.
- Don’t catch every exception in every function.
- Don’t use exception specifications.

---

## 17. C++ Sonar Code Quality Checks Standards

- SonarQube is used for automated code quality checks.
- Quality profiles are reviewed and updated periodically.
- Issues are tracked and resolved via JIRA.
- Web and API security standards are enforced (e.g., OWASP, SANS).

---

## 18. Appendix

### 18.1 Sources of Code Smells and Bugs

- Too much information
- Dead code
- Vertical separation
- Inconsistency
- Clutter
- Artificial coupling
- Incorrect behavior at boundaries
- Overridden safeties
- Duplication
- Misplaced responsibility
- Imprecision
- Structure over convention

### 18.2 Unit Tests

- Follow **F.I.R.S.T** principles: Fast, Independent, Repeatable, Self-Validating, Timely.
- Use coverage tools.
- Test boundaries.
- Keep tests clean.

### 18.3 Effectiveness in Programming C++

Common issues to avoid:

- Duplicated code
- Long methods
- Large classes
- Divergent change
- Feature envy
- Data clumps
- Excessive switch statements
- Lazy classes
- Temporary fields
- Message chains
- Middle man
- Inappropriate intimacy
- Unnecessary comments

### 18.4 Secure Software Development Standard (Synopsis)

- Know security standards and policies.
- Document code.
- Use version control.
- Review before deployment.
- Control access.
- Handle sensitive/test/production data appropriately.

---

*This document is intended for internal use and is reviewed annually to ensure alignment with the latest C++ standards and best practices.*
