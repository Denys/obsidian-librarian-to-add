"""Deterministic search over index records."""

from __future__ import annotations

from dataclasses import dataclass, field

from obsidian_librarian.indexer import IndexRecord


@dataclass(frozen=True)
class SearchHit:
    path: str
    scope: str
    score: int
    matched_fields: list[str]
    snippet: str


@dataclass
class SearchSummary:
    query: str
    scope: str
    searched_files: int
    matched_files: int
    hits: list[SearchHit] = field(default_factory=list)


def search_index(records: list[IndexRecord], query: str, scope: str) -> SearchSummary:
    q = query.strip().lower()
    if not q:
        raise ValueError("Query must not be empty")

    hits: list[SearchHit] = []
    for rec in records:
        score = 0
        fields: list[str] = []
        if q in rec.path.lower():
            score += 5
            fields.append("path")
        if q in rec.title.lower():
            score += 6
            fields.append("title")
        if any(q in t.lower() for t in rec.tags):
            score += 4
            fields.append("tags")
        if any(q in h.lower() for h in rec.headings):
            score += 4
            fields.append("headings")
        if any(q in w.lower() for w in rec.wikilinks):
            score += 3
            fields.append("wikilinks")
        if any(q in v.lower() for v in rec.frontmatter.values()):
            score += 3
            fields.append("frontmatter")
        if any(q in r.lower() for r in rec.source_refs):
            score += 2
            fields.append("source_refs")
        if any(q in s.lower() for s in rec.snippets):
            score += 1
            fields.append("content")

        if score > 0:
            hits.append(
                SearchHit(
                    path=rec.path,
                    scope=rec.scope,
                    score=score,
                    matched_fields=sorted(set(fields)),
                    snippet=rec.snippets[0] if rec.snippets else "",
                )
            )

    hits.sort(key=lambda h: (-h.score, h.path))
    return SearchSummary(
        query=query,
        scope=scope,
        searched_files=len(records),
        matched_files=len(hits),
        hits=hits,
    )
