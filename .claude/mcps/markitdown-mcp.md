# Markitdown MCP — .claude/mcps/markitdown-mcp.md

Purpose: convert PDF/Word/Excel/image/audio files into Markdown for ingestion
into `ai` capability's `rag-skill`/`embeddings-skill`.

Source: Microsoft, `github.com/mcp/microsoft/markitdown`.

Config

- `max_file_size_mb`: cap input file size

Usage

- Run as a preprocessing step before chunking/embedding; do not feed raw
  binary files directly into RAG ingestion.

Security

- Treat converted content as untrusted input until `hallucination-check`/
  `ai-output-validator` has run over anything derived from it.
