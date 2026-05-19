# 31 — Tool Contracts

Tool contracts define what each component may read, write, return, and refuse.

## Contract format

```text
tool_name:
  purpose:
  inputs:
  outputs:
  reads:
  writes:
  risk:
  refusal_conditions:
  tests:
```

## v0.1 tools

| Tool | Purpose | Reads | Writes | Risk |
|---|---|---|---|---:|
| `list_files` | Discover inbox files | inbox directory | none | Low |
| `read_file` | Read Markdown/TXT content | source file | none | Low |
| `parse_source` | Extract basic title/body/TODOs | source text | none | Low |
| `render_source_note` | Create Markdown note text | parsed source | none | Low |
| `write_staged_note` | Write generated note | rendered note | `90_Staging/` | Medium |
| `validate_note` | Validate frontmatter and sections | staged note | none | Low |
| `generate_review_report` | Summarize results and warnings | run state | `review_report.md` | Low |

## Write constraints

`write_staged_note` must enforce:

- destination is inside configured staging directory;
- existing files are not overwritten by default;
- path traversal is blocked;
- raw source files are never modified;
- every write result is reported.

## Future tools

Future LLM, embedding, PDF, or Agents SDK tools must be opt-in and must preserve the same staging and provenance constraints.
