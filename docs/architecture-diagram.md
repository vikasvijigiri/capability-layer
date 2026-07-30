# UAIOS Architecture Diagram

Original ASCII diagram (preserved):

```
<big ASCII diagram from user>
```

I've split the architecture into per-plane Mermaid sources for easier editing and rendering. Each plane is in `docs/diagrams/` and can be rendered individually.

Files created:

- `docs/diagrams/architecture-control.mmd`
- `docs/diagrams/architecture-intelligence.mmd`
- `docs/diagrams/architecture-execution.mmd`
- `docs/diagrams/architecture-knowledge.mmd`
- `docs/diagrams/architecture-optimization.mmd`
- `docs/diagrams/architecture-governance.mmd`
- `docs/diagrams/architecture-observability.mmd`
- `docs/diagrams/architecture-infrastructure.mmd`

Render each file with the Mermaid CLI, for example:

```bash
npm install -g @mermaid-js/mermaid-cli
mmdc -i docs/diagrams/architecture-control.mmd -o docs/diagrams/architecture-control.png
```

You can also render all of them in a loop and stitch images together if you want a single combined graphic.

If you'd like, I can render and attach PNG/SVG exports for each plane now.