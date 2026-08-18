---
name: p7-code-review
description: "P7 code review rules derived from historical PR feedback for the P7 Pricing Engine and platform. Use when: reviewing any P7 code change — covers all layers (Pricing Engine C++, Frontend, Middleware, Database)."
systems: [p7]
extends: skills/common/code-review
argument-hint: "Paste or describe the code changes to review"
---

# gts.p7.pricingengine Code Review

**Extends: skills/common/code-review**

Applies the shared review discipline ([`skills/common/code-review`](../../../common/code-review/SKILL.md) — independent assessment, holistic assessment, multi-model review, false-positive avoidance, severity→verdict, scope-to-change, coverage ledger, output skeleton) and delegates the **code-review concerns** (correctness, quality, security, performance, guideline, dependency, intent, architecture) to the [`code-review-lens`](../../../common/code-review-lens/SKILL.md) brain. This skill adds the **P7-specific** rules below: the review output format (with P7 verdict words), the Holistic PR Assessment's P7 log-ID rules, thread-safety/locking order, `LOGGER_TO`/`LOGWAR_TO` IDs, `library/gen` templates, strong typed IDs, double-vs-float pricing, Crow/PEDB/CMDB and RestEndPoints conventions, and Zustand/AG Grid/Socket.IO patterns. These rules were extracted from recurring reviewer feedback across all PR states in `dev/gts.p7.pricingengine`. Don't build the code, only read it.

**Reviewer mindset:** Be polite but very skeptical. Your job is to help speed the review process for maintainers, which includes not only finding problems the PR author may have missed but also questioning the value of the PR in its entirety. Treat the PR description and linked issues as claims to verify, not facts to accept. Question the stated direction, probe edge cases, and don't hesitate to flag concerns even when unsure.

## Review Output Format

When presenting the final review (whether as a PR comment or as output to the user), use the following structure. This ensures consistency across reviews and makes the output easy to scan.

> 📝 **AI-generated content disclosure:** When posting review content to GitHub (PR review comments, PR comments) under a user's credentials — i.e., the account is **not** a dedicated "copilot" or "bot" account/app — you **MUST** include a concise, visible note (e.g. a `> [!NOTE]` alert) indicating the content was AI/Copilot-generated. Skip this if the user explicitly asks you to omit it.

### Structure

```
## 🤖 Copilot Code Review — PR #<number>

### Holistic Assessment

**Motivation**: <1-2 sentences on whether the PR is justified and the problem is real>

**Approach**: <1-2 sentences on whether the fix/change takes the right approach>

**Summary**: <✅ LGTM / ⚠️ Needs Human Review / ⚠️ Needs Changes / ❌ Reject>. <2-3 sentence summary of the overall verdict and key points. If "Needs Human Review," explicitly state which findings you are uncertain about and what a human reviewer should focus on.>

---

### Detailed Findings

#### ✅/⚠️/❌ <Category Name> — <Brief description>

<Explanation with specifics. Reference code, line numbers, interleavings, etc.>

(Repeat for each finding category. Group related findings under a single heading.)
```

### Guidelines

- **Holistic Assessment** comes first and covers Motivation, Approach, and Summary.
- **Detailed Findings** uses emoji-prefixed category headers:
    - ✅ for things that are correct / look good (use to confirm important aspects were verified)
    - ⚠️ for warnings or impactful suggestions (should fix, or follow-up)
    - ❌ for errors (must fix before merge)
    - 💡 for minor suggestions or observations (nice-to-have)
- **Cross-cutting analysis** should be included when relevant: check whether related code (sibling types, callers, other platforms) is affected by the same issue or needs a similar fix.
- **Test quality** should be assessed as its own finding when tests are part of the PR.
- **Summary** gives a clear verdict: LGTM (no blocking issues — use only when confident), Needs Human Review (code may be correct but you have unresolved concerns or uncertainty that require human judgment), Needs Changes (with blocking issues listed), or Reject (explaining why this should be closed outright). **Never give a blanket LGTM when you are unsure.** When in doubt, use "Needs Human Review" and explain what a human should focus on.
- Keep the review concise but thorough. Every claim should be backed by evidence from the code.

### Verdict Consistency Rules

The summary verdict **must** be consistent with the findings in the body. Follow these rules:

1. **The verdict must reflect your most severe finding.** If you have any ⚠️ findings, the verdict cannot be "LGTM." Use "Needs Human Review" or "Needs Changes" instead. Only use "LGTM" when all findings are ✅ or 💡 and you are confident the change is correct and complete.

2. **When uncertain, always escalate to human review.** If you are unsure whether a concern is valid, whether the approach is sufficient, or whether you have enough context to judge, the verdict must be "Needs Human Review" — not LGTM. Your job is to surface concerns for human judgment, not to give approval when uncertain. A false LGTM is far worse than an unnecessary escalation.

3. **Separate code correctness from approach completeness.** A change can be correct code that is an incomplete approach. If you believe the code is right for what it does but the approach is insufficient (e.g., treats symptoms without investigating root cause, silently masks errors that should be diagnosed, fixes one instance but not others), the verdict must reflect the gap — do not let "the code itself looks fine" collapse into LGTM.

4. **Classify each ⚠️ and ❌ finding as merge-blocking or advisory.** Before writing your summary, decide for each finding: "Would I be comfortable if this merged as-is?" If any answer is "no," the verdict must be "Needs Changes." If any answer is "I'm not sure," the verdict must be "Needs Human Review."

5. **Devil's advocate check before finalizing.** Re-read all your ⚠️ findings. For each one, ask: does this represent an unresolved concern about the approach, scope, or risk of masking deeper issues? If so, the verdict must reflect that tension. Do not default to optimism because the diff is small or the code is obviously correct at a syntactic level.

---

## Holistic PR Assessment

Before reviewing individual lines of code, evaluate the PR as a whole. Consider whether the change is justified, whether it takes the right approach, and whether it will be a net positive for the codebase.

### Motivation & Justification

- **Challenge every addition with "Do we need this?"** New code, APIs, abstractions, and flags must justify their existence. If an addition can be avoided without sacrificing correctness or meaningful capability, it should be.

### Approach & Alternatives

- **Check whether the PR solves the right problem at the right layer.** Look for whether it addresses root cause or applies a band-aid. Prefer fixing the actual source of an issue over adding workarounds to production code.
- **When a PR takes a fundamentally wrong approach, redirect early.** Don't iterate on implementation details of a flawed design. Push back on the overall direction before the contributor invests more time.
- **Ask "Why not just X?" — always prefer the simplest solution.** When a PR uses a complex approach, challenge it with the simplest alternative that could work. The burden of proof is on the complex solution.

### Cost-Benefit & Complexity

- **Explicitly weigh whether the change is a net positive.** A performance trade-off that shifts costs around is not automatically beneficial. Demand clarity that the change is a win in the typical configuration, not just in a narrow scenario.
- **Reject overengineering — complexity is a first-class cost.** Unnecessary abstraction, extra indirections, and elaborate solutions for marginal gains are actively rejected.
- **Every addition creates a maintenance obligation.** Long-term maintenance cost outweighs short-term convenience. Code that is hard to maintain, increases surface area, or creates technical debt needs stronger justification.

### Risk & Compatibility

- **Assess regression risk proportional to the change's blast radius.** High-risk changes to stable code need proportionally higher value and more thorough validation.

### Codebase Fit & History

- **Ensure new code matches existing patterns and conventions.** Deviations from established patterns create confusion and inconsistency. If a rename or restructuring is warranted, do it uniformly in a dedicated PR — not piecemeal.
- **Check whether a similar approach has been tried and rejected before.** If a prior attempt didn't work, require a clear explanation of what's different this time.
- **Message log IDs in `LOGGER_TO` and `LOGWAR_TO` must be assigned and unique.** The second argument of logger macros must be a unique number not reused elsewhere. `__LOG_MESSAGE_ID__` must not remain in committed code.
- **When behavior changes, update related log statements.** Keep logs aligned with control flow and payload changes so diagnostics remain reliable.
---

## Correctness & Safety

### Error Handling & Assertions

- **Challenge exception swallowing that masks unexpected errors.** When a PR adds try/catch blocks that silently discard exceptions (`catch { continue; }`, `catch { return null; }`), question whether the exception represents a truly expected, recoverable condition or an unexpected error signaling a deeper problem (race conditions, memory corruption, build environment issues). Silently catching exceptions that "shouldn't happen" hides root causes and makes debugging harder. The default disposition should be to let unexpected exceptions propagate or fail fast so the real issue gets investigated.
- **Validate JSON node type/shape before conversion in REST handlers.** Check fields before calling conversions like `.i()`/extracting typed values.
- **Validate full REST input before mutating state.** In endpoint handlers, validate payload shape, typed IDs, and required fields first; avoid partial updates/side effects when later validation fails.
- **Guard optional values explicitly; avoid sentinel fallbacks.** Use `has_value()`/`value_or(...)` appropriately and avoid magic fallback values that can hide invalid states.

### Thread Safety

- **Prevent double locking of `SharedMutex`, `std::shared_mutex`, and `std::mutex`.** When there is a need to add a lock, make sure the same lock is not acquired by the caller and its parent. If it is, pass down a lock token through arguments.
- **Locking order** There is strict order of locking. `_sessionDataMutex` of `SessionDataAccess` must not be locked prior to `DataAccessMutex`. `WhatIfMutex` must not be locked after `DataAccessMutex`.
- **Use explicit lock-token discipline for shared caches.** Access to `DataAccess` and `ComputedDataAccess` in concurrent paths must hold the correct lock/token for the full access lifetime.
- **Assume Crow handlers and background workers execute concurrently.** Protect shared mutable state accordingly and keep lock ordering consistent across code paths.
- **Treat cache rebuild/refresh flows as race-prone.** Review concurrent readers/writers during cache updates.
- **Minimize exclusive lock scope and re-check after lock transitions.** Prefer `std::shared_lock` for read-only paths and re-validate dependent state when upgrading/changing lock context.

### Correctness Patterns

- **Fix root cause, not symptoms or workarounds.** Investigate and fix the root cause rather than adding workarounds or suppressing warnings.
- **Prefer safe code over unsafe micro-optimizations.** 
- **Delete dead code and unnecessary wrappers.** Remove dead code, unnecessary wrappers, obsolete fields, and unused variables when encountered or when the only caller changes.
- **Prefer correct-by-construction designs.** Prefer designs that are correct by construction (e.g., scanning IL) over manually maintained parallel data structures. A missed optimization is better than silent bad codegen.
- **Allocate on the correct loader allocator for collectibility.** When allocating runtime data structures for generic instantiations, use the correct loader allocator accounting for collectibility of type arguments.
- **Modify templates instead of generated files** Every file in `library/gen` is generated by `tool/generateSqlCpp.py` using templates defined in `tool/templates`. Don't modify the generated files, modify the template instead.
- **Use strong typed IDs consistently.** Prefer `ProductId`, `InstrumentId`, `ProductExpirationId`, etc. over ambiguous/raw IDs in interfaces and mappings.
- **Prefer `double` (or explicit templates) over `float` in pricing/vola paths unless measured evidence justifies `float`.**
- **Add explicit precondition checks in interpolation/math helpers.** Guard minimum sizes and invalid states early.
- **Require targeted tests for behavior changes.** Endpoint and pricing behavior changes should come with `testRestAPI.py` coverage or focused unit tests.

### Allocation Avoidance

- **Avoid closures and allocations in hot paths.** When a lambda captures locals creating a closure, consider using a static delegate with a state parameter (value tuple). Avoid string concatenation; use span-based operations.
- **Pre-allocate collections when size is known.**

### Code Structure for Performance

- **Place cheap checks before expensive operations.** Order conditionals so cheapest/most-common checks come first. Move expensive work after early-exit checks.
- **Avoid O(n²) patterns in collections and hot paths.** 
- **Cache repeated accessor calls in locals.** Store the result of repeated property/getter calls in a local variable.
- **Avoid repeated lock-heavy clone/lookups in loops.** Fetch once and reuse instead of repeatedly calling `DataAccess`/`ComputedDataAccess` methods that lock and copy.
- **Compute constant data at compile time, not execution time.** In interpreter and similar hot paths, pre-compute metadata lookups and type checks during the compilation phase.
- **Consider scalability, not just throughput.** Evaluate whether data structures, caches, and locking strategies will hold up at high cardinality or under concurrent load. Watch for unbounded collection growth, lock contention that worsens with core count, and O(1) assumptions that break at scale.

## Code Style & Formatting

For language-level standards (C++ naming, formatting, Sonar compliance), refer to the `coding-guidelines` common skill. P7-specific review rules below take precedence.

- **Use well-named constants instead of magic numbers.** No raw hex or decimal constants without explanation. Don't duplicate magic constants across files.
- **Name methods to accurately reflect their behavior.** Update names when behavior changes. `get*` implies a return value; use `print*/display*` for void. `ThrowIf` not `ThrowExceptionIf`.
- **Prefer early return to reduce nesting.** Use early returns for short/error cases to avoid unnecessary nesting. Put the error case first, success return last.
---

## Consistency with Codebase Patterns

### Code Reuse & Deduplication

- **Extract duplicated logic into shared helper methods.** Fix improvements inside shared helpers so all callers benefit.
- **Move shared code to shared files, not duplicated across runtimes.** When identical code exists across CoreCLR and NativeAOT, move it to the shared partition (using `#if !MONO` if needed).
- **Use existing APIs instead of creating parallel ones.** Before introducing new types, enums, or helpers, check if existing ones serve the same purpose. Fix existing utilities rather than introducing duplicates.
- **Use generated enums/value-name mappings instead of ad-hoc literals.** Prefer `Gen*` constants and mapping helpers for externally visible labels.
- **Expose domain semantics as names, not opaque numbers.** Keep fit/source types readable and stable in REST payloads.
- **Keep endpoint naming and placement consistent with `app/RestEndPoints`.** New endpoint behavior should follow existing file/class structure.
- **Delete dead code and unused declarations aggressively.** When removing code, also remove helper methods, enum values, function declarations, and resx strings that are no longer used.
---

## Documentation & Comments

- **Comments should explain why, not restate code.** Delete comments like `// Get the types` that just duplicate the code in English. Don't include historical context about why code changed.
- **Delete or update obsolete comments when code changes.** Stale comments describing old behavior are worse than no comments.
- **Don't duplicate comments on interface implementations.** Documentation comments belong on the interface definition. Duplicating leads to divergence.
---
