# T7 Knowledge Base — Output Template

Use this template for every response. Do not deviate from the structure.
The Synthesis Agent parses this format to build the final user-facing answer.

Select the section that matches the query type: **coding-guideline**,
**component-info**, **ownership**, or **terminology**. Use exactly one section per response.

---

## When a Coding Guideline Answer Was Found

```
QUERY_TYPE: coding-guideline
SOURCE: <guideline document name and version, e.g. "C++ Coding Guidelines v1.4">
CONFIDENCE: <high | medium | low>

SUMMARY:
<A concise explanation of the relevant rule or standard in relation to the query.
State what is required, what is forbidden, and any rationale given in the document.
2-4 sentences.>

REFERENCES:
  - <document name> § <section number and title> — <one-line description>
  (at least one section reference is mandatory)

RULE:
  <The verbatim rule text or the most directly relevant excerpt from the guideline.
  If the document provides a code example illustrating the rule, include it here.>

NOTES:
  <Optional. Use only when one of the following applies:
  - The rule has documented exceptions or language-version restrictions
  - A related rule in another section qualifies or overrides this one
  - SonarQube enforcement details are relevant to the query
  Omit this field entirely if there are no notable observations.>
```

---

## When a Component Info Answer Was Found

```
QUERY_TYPE: component-info
SOURCE: <reference document, e.g. "T7 Component Map" or "T7 Module Map">
CONFIDENCE: <high | medium | low>

SUMMARY:
<A concise description of the component, its role in the T7 system, and its location.
2-4 sentences.>

REFERENCES:
  - <document name> — <section or table row identifying the component>
  (at least one reference is mandatory)

DETAILS:
  Repository:   <repo path>
  Component:    <component identifier, e.g. gts.eurex.matcher>
  Module:       <module name if applicable>
  Responsibility: <what this component is responsible for>
  Directory:    <directory path within the release baseline, if available>

NOTES:
  <Optional. Use for related components, deprecated paths, or split ownership.
  Omit this field entirely if there are no notable observations.>
```

---

## When an Ownership Answer Was Found

```
QUERY_TYPE: ownership
SOURCE: T7 Component Ownership
CONFIDENCE: <high | medium | low>

SUMMARY:
<A concise statement of which team owns the component or repository and what their scope covers.
1-3 sentences.>

REFERENCES:
  - T7 Component Ownership — row: <repository / component identifier>
  (at least one row reference is mandatory)

DETAILS:
  Repository:  <repo path>
  Component:   <component identifier>
  Department:  <owning department / team name>

NOTES:
  <Optional. Use when ownership is shared, unclear, or has recently changed.
  Omit this field entirely if there are no notable observations.>
```

---

## When a Terminology Answer Was Found

```
QUERY_TYPE: terminology
SOURCE: T7 Terminology
CONFIDENCE: <high | medium | low>

SUMMARY:
<A plain-language explanation of the term in the T7 context. Include any common
abbreviations, synonyms, or easily confused related terms. 2-4 sentences.>

REFERENCES:
  - T7 Terminology — entry: <term>
  (at least one entry reference is mandatory)

DEFINITION:
  <The verbatim definition from the T7 Terminology reference, or the closest
  matching entry if no exact match exists.>

NOTES:
  <Optional. Use when the term has different meanings in different T7 subsystems,
  or when a related term is frequently confused with this one.
  Omit this field entirely if there are no notable observations.>
```

---

## When Nothing Was Found

```
QUERY_TYPE: <coding-guideline | component-info | ownership | terminology>
SOURCE: <reference document consulted>
CONFIDENCE: none

NOT_FOUND:
  Query received: <repeat the sub-query as received>
  Sources consulted:
    - <reference document> — <result: e.g. "no matching entry", "section not present", "unrelated matches">
    - <reference document> — <result>
  Conclusion: <Brief statement on why the answer was not located. Is this likely a naming
  convention issue, a term not yet in the glossary, or genuinely absent from the references?>
```

---

## Confidence Level Guide

| Level | When to Use |
|-------|-------------|
| **high** | The exact answer was found. The content directly and unambiguously addresses the sub-query. References are precise. |
| **medium** | Closely related content was found (e.g. a parent section but not the exact rule, or one variant but not all). The answer is likely correct but incomplete. |
| **low** | Only tangentially related content was found. The result may point in the right direction but does not directly answer the sub-query. |
| **none** | No relevant content was found after exhausting all applicable sources. |
