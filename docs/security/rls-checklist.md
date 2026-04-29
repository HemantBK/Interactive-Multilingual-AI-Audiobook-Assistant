# RLS verification runbook

Build plan A2 §6 threat #7. Run before every public deploy + after any
migration that touches user-facing tables. Failures here are P0.

## Setup

Two distinct accounts, both with the magic-link flow:

```
A: alice@aria-test.example  → user_id = <UUID-A>
B: bob@aria-test.example    → user_id = <UUID-B>
```

Sign in to the production-equivalent stack as A, upload a sample PDF.
Wait for `status='ready'`. Note the `documents.id` of A's doc; call it
`<DOC-A>`.

Sign out, then sign in as B in the same browser. Open DevTools.

## Tests

Each test should **fail closed**: if the response shows A's data, the
RLS policy is broken or missing.

### 1. `documents` row visibility

```js
// Run in DevTools while signed in as B
await fetch('/documents', {
  headers: { Authorization: `Bearer ${session.access_token}` }
}).then(r => r.json())
```

Expected: zero rows belonging to `<UUID-A>`. Only rows where
`user_id = <UUID-B>`.

### 2. `documents/{id}` direct fetch

```js
await fetch(`/documents/${'<DOC-A>'}`, {
  headers: { Authorization: `Bearer ${session.access_token}` }
})
```

Expected: `404 Document not found` — not `200` with A's data.

### 3. `document_chunks` cross-user retrieval

Try to RAG B's question against A's document:

```js
await fetch('/rag/ask', {
  method: 'POST',
  headers: { Authorization: `Bearer ${session.access_token}`, 'Content-Type': 'application/json' },
  body: JSON.stringify({ document_id: '<DOC-A>', question: 'What is on page 1?' })
})
```

Expected: `404 Document not found`.

### 4. Storage object visibility

```js
const { data: signed } = await supabase.storage
  .from('documents')
  .createSignedUrl('<UUID-A>/<DOC-A>/original.pdf', 60);
```

Expected: `error.message` indicates RLS denial. The signed URL must NOT
be issued.

### 5. `conversations` rows

```js
await supabase.from('conversations').select('*').eq('user_id', '<UUID-A>')
```

Expected: empty `data`.

### 6. `audit_log` rows

```js
await supabase.from('audit_log').select('*').eq('user_id', '<UUID-A>')
```

Expected: empty `data`.

### 7. `idempotency_keys`

Same shape — empty.

### 8. RPC `search_chunks`

```js
await supabase.rpc('search_chunks', {
  p_document_id: '<DOC-A>',
  p_query_embedding: '[0.1,0.2,…]',
  p_match_count: 5
})
```

Expected: empty array. The function is `security invoker` so RLS
applies; the bge-m3 vector is irrelevant since no rows match.

### 9. Backend-only tables (audio_cache, translation_cache, prompts)

These have no user-facing RLS by design — backend uses `admin_client`.
From a client query, expect zero rows. If a client query returns rows
from these tables, **service-role key has leaked into the browser** —
P0.

```js
await supabase.from('audio_cache').select('*').limit(1)
await supabase.from('translation_cache').select('*').limit(1)
await supabase.from('prompts').select('*').limit(1)
```

Expected: empty `data` for all three.

## Pass criteria

All 9 tests pass. Capture results in a `docs/security/runs/<date>.md`
file (timestamped) and link from the Day 26 review.

## Failure → action

Any test returning A's data while signed in as B: file a P0, halt the
deploy, page the operator. Do NOT promote to production until fixed
and the runbook re-runs clean.
