# Features Research: DocuData

**Project:** DocuData — Automated Project Documentation for Data Teams
**Dimension:** Features
**Confidence:** MEDIUM overall (analysis from training knowledge + CLAUDE.md design doc)

---

## Key Findings

- No mainstream tool auto-ingests heterogeneous files (kanban screenshots, PDFs, DOCX task docs) and extracts structured knowledge from them. This is DocuData's core differentiator.
- "Just use ChatGPT" is the actual competition, not Confluence. The defensible gap is the structured 6-field schema + sprint attribution + cross-sprint context accumulation.
- Authentication is the single biggest scope creep trap — adds 1-2 days, no validated need for shared-space MVP.
- The `decisoes` doc type (technical decision log across full project lifetime) is the highest-signal differentiator.
- Copy-to-clipboard is table stakes — the exit ramp that makes the tool usable.

---

## Table Stakes (must have or the tool feels broken)

| Feature | Why Expected | Complexity |
|---------|--------------|------------|
| Create project (name, client, description) | Container for everything | Low |
| List projects, navigate to project | Home screen expectation | Low |
| Upload file with sprint number + success/error feedback | Silent failure destroys trust | Low |
| View ingestion history grouped by sprint | Verify files were received before trusting generated output | Low |
| Generate all four document types on demand | Core value delivery | Medium |
| Markdown rendering in browser | Raw markdown reads as noise | Low |
| Copy generated document to clipboard | Primary exit ramp — paste into Confluence, Notion, Slack | Low |
| Handle DOCX, PDF, TXT, PNG, JPG/WEBP | Data team PMs produce all five types | Medium |
| Error feedback when extraction fails | Corrupted files must surface an error, not silently save empty JSON | Low |

## Differentiators (competitive advantage over "just use ChatGPT")

| Feature | Value Proposition | Complexity |
|---------|-------------------|------------|
| Structured 6-field extraction | ChatGPT gives prose; DocuData gives queryable fields that accumulate and compose | Medium |
| Sprint-scoped generation from accumulated context | "Generate retro for Sprint 3" with zero copy-paste | Medium |
| Multimodal ingestion (kanban screenshots, scanned PDFs) | No mainstream tool accepts a screenshot of a kanban board | Medium |
| Technical decision log (`decisoes` type) | No tool has this as a first-class concept; highest value for handoffs | Low (given infra) |
| Complete project document on demand (`completo` type) | One click replaces 2-hour writing session | Low (given infra) |
| Context accumulation (more uploads = richer output) | Progressive improvement within a project | Low (architectural) |
| Standardized output format enforced across all PMs | Eliminates "everyone documents differently" | Low |

## Anti-Features (do NOT build in v1)

| Anti-Feature | Why Avoid | Complexity Cost Avoided |
|--------------|-----------|------------------------|
| Authentication / login | Adds 1-2 days; entire team shares tool with no isolation need | High |
| Per-user project isolation | Requires auth first | High |
| Rich text editor for manual editing | Turns DocuData into Notion — PMs want to STOP writing | Very High |
| Comments / collaboration on documents | Confluence's core product | High |
| Notification system | Adds integration complexity | Medium |
| Export to DOCX or PDF | Clipboard is sufficient; export adds library dependencies | Medium |
| Auto-detection of sprint from filename | Ambiguous, error-prone | Medium |
| Search across ingested content | Requires full-text search infra; not validated | Medium-High |
| Dashboard analytics | Vanity metrics for MVP | Medium |
| Versioning of generated documents | Regenerate-on-demand is sufficient | Medium |
| Mobile-optimized UI | PMs document at a desk; desktop-first is correct | Medium |

---

## Feature Dependencies

```
Project creation
  → File upload / ingestion (requires project)
    → Ingestion history view (requires ≥1 ingestion)
      → Document generation (requires ingestions)
        → Markdown rendering (requires generated doc)
          → Copy to clipboard (requires rendered doc)

Sprint number (at upload)
  → Sprint-scoped generation (sprint_status, sprint_retro)

All project ingestions (all sprints)
  → Cross-sprint generation (decisoes, completo)
```

---

## Data Team PM-Specific Insights

1. **Artifacts are heterogeneous** — DOCX tasks, kanban screenshots, client PDFs, TXT meeting notes in the same sprint. Multimodal ingestion is a real gap.
2. **Decisions matter more than tasks for handoff** — `decisoes` field and doc type are the highest-value institutional knowledge capture.
3. **Client context is fragile** — `contexto_cliente` captures what lives only in verbal conversations and disappears at project end.
4. **Retros are high-pain** — frequently skipped because writing them takes longer than the sprint. Auto-generation directly addresses this.
5. **The user does not want a new writing tool** — any feature requiring PMs to write in DocuData replicates the exact problem they have.

---

## MVP Build Order (3-Day Recommendation)

1. Project CRUD — Day 1, ~2h
2. File upload + extraction graph end-to-end — Day 1-2, core work
3. Ingestion history view — Day 2, trust signal
4. All four document generation types — Day 2-3, value delivery
5. Markdown rendering + copy button — Day 3, exit ramp

---

## Open Questions

- Does the CITi data subárea use any existing tool (Notion, Confluence, Google Docs) where DocuData output should integrate?
- How large are typical PDF files uploaded by PMs? (latency and context window concern for >50 pages)
- What does "successful extraction" look like to a PM? (qualitative bar for prompt engineering)
