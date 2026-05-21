# 12 — Phase 10 Vault-Aware Librarian Roadmap

## Executive summary

Phase 10 starts as a **read-only vault-aware librarian**: deterministic inventory + retrieval first, then optional cited synthesis. It is **not** an autonomous curator and it must not claim global knowledge beyond retrieved files.

The first milestone is planning-only (Phase 10.0). Implementation should start with deterministic index/search and only later add optional LLM synthesis. Agents SDK remains a later orchestration option, not a prerequisite.

## Reality check

- The model is **not** automatically aware of the vault because files exist on disk.
- The vault is a **data source**, not implicit context.
- “Agent” means model + tools + runtime + permissions + guardrails; it does not imply correctness.
- Retrieval results are partial unless the system explicitly proves scope coverage.

## User modes (A+B)

Initial target modes:

- `ask --scope vault` → answer from trusted vault content only.
- `ask --scope staging` → answer from `90_Staging` only.
- `ask --scope vault-and-staging` → answer from both, while labeling trusted vs staged evidence separately.

Every answer must report:

- searched scope,
- files/chunks used,
- citations/evidence,
- confidence/coverage,
- gaps / insufficient evidence.

## Phase 10 roadmap

| Phase | Goal | Writes? | LLM? | Agents SDK? |
|---:|---|---|---|---|
| 10.0 | Roadmap/design only | No | No | No |
| 10.1 | Deterministic vault/staging inventory | No | No | No |
| 10.2 | Deterministic retrieval/search | No | No | No |
| 10.3 | Read-only ask with cited synthesis | No | Optional | No |
| 10.4 | Answer contract and guardrails | No | Optional | No |
| 10.5 | Optional Agents SDK orchestration layer | No by default | Yes | Yes |
| 10.6 | Future promotion/curation design | Design only | Maybe | Maybe |

### Phase 10.0 — Roadmap/design only

Deliverables:

- this roadmap document;
- implementation boundaries and acceptance criteria for 10.1–10.6.

Non-goals:

- no code;
- no dependency changes;
- no runtime changes.

Done criteria:

- roadmap is explicit about safety, scope reporting, and phased implementation.

### Phase 10.1 — Deterministic vault inventory/index

Deliverables:

- markdown scan with deterministic metadata extraction;
- inventory fields: path, scope, title, headings, frontmatter, tags, wikilinks, source refs, status, modified time;
- trusted-vault vs staging distinction.

Constraints:

- no LLM;
- no writes;
- no network.

Done criteria:

- inventory can be generated deterministically for fixture vaults;
- scope labeling is correct for trusted/staging notes.

### Phase 10.2 — Deterministic retrieval/search

Deliverables:

- keyword/title/tag/frontmatter/link/heading search;
- candidate note snippets;
- searched scope and result count.

Constraints:

- no LLM required;
- deterministic ranking heuristics only.

Done criteria:

- retrieval tests pass against fixture vault + staging notes;
- scope separation and ranking behavior are deterministic.

### Phase 10.3 — Read-only `ask` command

Deliverables:

- `ask` command that first retrieves deterministically;
- optional OpenAI Responses synthesis from retrieved notes only;
- cited answer output (files/chunks).

Constraints:

- no writes;
- mock model path in tests;
- fail safely when evidence is insufficient.

Done criteria:

- `ask` never asserts uncited claims;
- insufficient evidence response path is explicit and tested.

### Phase 10.4 — Answer contract and scope guardrails

Deliverables:

- strict answer envelope with evidence/scope/coverage/gaps;
- fact vs inference vs assumption vs recommendation separation;
- no hidden “global vault awareness” claims.

Done criteria:

- output contract enforced and regression tested;
- scope and evidence sections always present.

### Phase 10.5 — Optional Agents SDK orchestration layer

Deliverables:

- optional wrapper that exposes deterministic index/search/ask functions as tools;
- read-only defaults;
- guardrails around scope, path safety, and no-write policy.

Constraints:

- only after 10.1–10.4 stabilize;
- no MCP initially;
- no web search initially;
- no shell tool;
- no deletion/promotion.

Done criteria:

- tool contracts validated;
- guardrail behavior tested at input/output/tool boundaries.

### Phase 10.6 — Future staged curation/promotion design

Deliverables:

- design-only proposal for human-approved promotion flow;
- explicit separation from `ask` mode.

Constraints:

- no implementation in this phase;
- no autonomous vault mutation.

Done criteria:

- promotion requires explicit human approval in design contract.

## Proposed command interfaces (provisional)

```bash
obsidian-librarian index --vault . --scope vault
obsidian-librarian search "daisy reverb" --vault . --scope vault-and-staging
obsidian-librarian ask "What do I know about Daisy reverbs?" --vault . --scope vault
obsidian-librarian ask "What changed in staging?" --vault . --scope staging
```

Names remain provisional if existing CLI architecture suggests better alignment.

## Proposed deterministic index record

```json
{
  "path": "relative/path.md",
  "scope": "vault|staging",
  "title": "string",
  "headings": ["string"],
  "tags": ["string"],
  "wikilinks": ["string"],
  "frontmatter": {},
  "source_refs": ["string"],
  "status": "staged|trusted|unknown",
  "modified_time": "string",
  "snippets": ["string"]
}
```

Vector DB is out-of-scope for first implementation.

## Retrieval strategy (deterministic first)

Initial retrieval should combine deterministic signals:

- filename match,
- title match,
- tag match,
- heading match,
- wikilink match,
- frontmatter/source_ref match,
- plain-text keyword match.

Semantic/vector retrieval is a future optional upgrade only.

## Answer contract (for ask mode)

Each answer should include sections in this order:

1. **Answer**
2. **Evidence used**
3. **Searched scope**
4. **Files searched / matched**
5. **Confidence / coverage**
6. **Gaps / not found**
7. **Suggested next actions**

## Safety constraints (10.1–10.5)

Explicitly forbidden:

- deletion,
- overwrite,
- permanent vault writes,
- autonomous promotion,
- arbitrary shell,
- MCP,
- web search,
- embeddings/vector DB,
- hidden persistent memory,
- uncited model-memory claims.

## Test strategy

Deterministic tests required:

- fixture trusted vault notes,
- fixture staging notes,
- indexer tests,
- retrieval ranking tests,
- scope separation tests,
- ask command tests with mock LLM,
- insufficient-evidence behavior tests,
- no-write regression tests,
- no web/network in CI.

## Acceptance criteria summary

- 10.0 done when roadmap + constraints + done criteria are documented.
- 10.1 done when deterministic inventory passes fixture tests.
- 10.2 done when deterministic retrieval and scope reporting are tested.
- 10.3 done when read-only ask returns cited answers or explicit insufficiency.
- 10.4 done when answer contract and guardrails are enforced.
- 10.5 done when optional Agents SDK wrapper safely orchestrates existing deterministic tools.
- 10.6 done when promotion is documented as human-approved design only.

## Open questions

1. Which folders count as trusted vault folders by default?
2. Should `90_Staging` be included by default or explicit-only?
3. Should enriched notes be searchable by default?
4. How should citations point to files/headings/line ranges?
5. Should index be persisted on disk or built on demand first?
6. When, if ever, should vector retrieval be introduced?
7. At what stability gate should Agents SDK be introduced?

## Upgrade path

read-only deterministic search  
→ cited LLM answer synthesis  
→ guarded agent runner  
→ staged curation  
→ human-approved promotion  
→ optional web intake later

## Implementation order recommendation

1. Merge/verify Phase 9 and live-test disposable enrichment.
2. Merge this Phase 10.0 roadmap.
3. Implement Phase 10.1 deterministic index.
4. Implement Phase 10.2 deterministic search.
5. Implement `ask` + optional cited LLM synthesis.
6. Consider optional Agents SDK orchestration after stability proof.

Primary design decision: the librarian must **prove what it searched** before it answers.
