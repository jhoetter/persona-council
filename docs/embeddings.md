# Provider-agnostic embeddings

Embeddings power semantic recall across persona memory. The provider is a
config choice — OpenAI is one adapter among several, not a requirement:

```bash
SONALOOP_EMBEDDINGS_PROVIDER=openai   # default when OPENAI_API_KEY is set
SONALOOP_EMBEDDINGS_PROVIDER=ollama   # local/open — EU & on-prem friendly
SONALOOP_EMBEDDINGS_PROVIDER=none     # explicit off
```

| Provider | Endpoint | Model env | Default model |
|---|---|---|---|
| `openai` | api.openai.com (urllib, no SDK) | `OPENAI_EMBEDDING_MODEL` | `text-embedding-3-small` |
| `ollama` | `OLLAMA_HOST` (default `http://localhost:11434`) `/api/embed` | `SONALOOP_OLLAMA_EMBED_MODEL` | `nomic-embed-text` |
| `none` | — | — | recall degrades to keyword + recency + importance |

Unset, the provider resolves to `openai` when a key is present, else `none` —
existing setups keep working; keyless setups run keyword-only until they opt
into a provider (no local-server auto-probing). `sonaloop info` shows the
resolved provider + model. The `PERSONA_COUNCIL_DISABLE_EMBEDDINGS=1` kill
switch beats everything. Everything is fail-soft: provider errors degrade to
keyword retrieval, never crash.

## Vector-space safety

Every stored vector carries its provider-qualified model id (OpenAI ids stay
un-namespaced, so existing vectors remain valid; Ollama ids are
`ollama:<model>`). Spaces never mix:

- **Recall** scores only vectors from the ACTIVE space; rows from another
  space are skipped and reported (`embedding_space_mismatch` on the recall
  result) instead of silently corrupting similarity.
- **Backfill** (`backfill-embeddings`) is space-aware: after a provider/model
  switch it re-embeds everything into the new space — switching is a config
  change plus one backfill, no code edits.
- **Snapshots** record which spaces produced the store's vectors
  (`manifest.embedding_models`); vectors themselves are re-derived on import,
  as before.
