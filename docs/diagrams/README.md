# Architecture drawings

| Drawing | Scope | Files |
| --- | --- | --- |
| Local application | Implemented ingestion, processing, database, API, and UI | [SVG](local-architecture.svg) · [PNG](local-architecture.png) |
| Production architecture | Proposed cloud ingestion, scaling, resilience, and storage | [SVG](production-architecture.svg) · [PNG](production-architecture.png) |
| Production controls | Onboarding, governance, monitoring, and operational response | [SVG](production-controls.svg) · [PNG](production-controls.png) |

Open [veritas-architecture.drawio](veritas-architecture.drawio) in Draw.io / diagrams.net to edit the three drawing pages. Cloud services and production governance controls are proposed, not deployed.

Regenerate the SVG and Draw.io files with:

```bash
python3 scripts/render_diagrams.py
```
