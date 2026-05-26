# T7 Code Agent — Output Template

Use this template for every response. Do not deviate from the structure.
The Synthesis Agent parses this format to build the final user-facing answer.

---

## When Code Was Found

```
SOURCE: t7codebase / <release-baseline>
CONFIDENCE: <high | medium | low>

SUMMARY:
<A concise paragraph explaining what the code does in relation to the query.
Write for an engineer who knows T7 but may not know this specific module.
Describe the behavior, the key decision points, and any notable conditions
or edge cases visible in the code. 3-6 sentences.>

REFERENCES:
  - <repository>/<path/to/file>:<line-start>-<line-end> — <one-line description>
  - <repository>/<path/to/file>:<line-start>-<line-end> — <one-line description>
  (list all relevant locations; at least one reference is mandatory)

SNIPPET:
  <The most directly relevant code excerpt. Include enough surrounding context —
  typically the full function or decision block — so the Synthesis Agent can
  quote it meaningfully. If multiple snippets from different files are needed,
  separate them with a comment line showing the file path.>

NOTES:
  <Optional. Use only when one of the following applies:
  - The implementation differs from what the name or concept suggests
  - There are TODOs, FIXMEs, or deprecated paths in the retrieved code
  - The logic varies significantly between instrument types, order types, or market states
  - A follow-up search in a related module would likely yield complementary results
  Omit this field entirely if there are no notable observations.>
```

---

## When No Code Was Found

```
SOURCE: t7codebase / <release-baseline>
CONFIDENCE: none

NOT_FOUND:
  Query received: <repeat the sub-query as received>
  Search strategies attempted:
    1. <search term or strategy used> — <result: e.g. "0 results", "unrelated matches">
    2. <search term or strategy used> — <result>
    3. <search term or strategy used> — <result>
  Conclusion: <Brief statement on why the implementation was not located. Is this likely
  a naming convention issue, a generated file, or genuinely absent from the indexed repos?>
```

---

## When the MCP Is Unavailable

```
ERROR: t7codebase MCP unavailable
Detail: <Error message or HTTP status returned by the tool>
Action: Retry once. If still unavailable, return this error to the Planner Agent.
```

---

## Confidence Level Guide

| Level | When to Use |
|-------|-------------|
| **high** | The exact implementation was found. The code directly and unambiguously addresses the sub-query. File and line references are precise. |
| **medium** | Closely related code was found (e.g. the calling layer but not the core logic, or one variant but not all). The answer is likely correct but incomplete. |
| **low** | Only tangentially related code was found. The result may point in the right direction but does not directly answer the sub-query. |
| **none** | No relevant code was found after exhausting at least three distinct search strategies. |
