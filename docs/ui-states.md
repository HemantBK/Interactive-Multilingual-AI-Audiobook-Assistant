# UI states inventory

Build plan A2 §12 requires three states on every fetch: empty, loading,
error. Day 19 audited and filled gaps; this file is the running checklist.
Day 21 a11y deep pass verifies that each state announces correctly.

## Convention

- **Loading** uses `role="status"` so screen readers announce changes politely.
- **Error** uses `role="alert"` so it interrupts.
- **Empty** is just text — no live region needed (no change to announce).
- **Toasts** add transient feedback (success / errors that aren't blocking).
  Persistent context-bound errors stay inline.

## Auth (`useAuth`)
| State | Surface |
|---|---|
| Loading | `<LoadingState />` in App `<main>` |
| Authenticated | App shell renders |
| Unauthenticated | `<SignInForm />` |
| SignInForm error | `role="alert"` red text under buttons |

## Documents list (`useDocuments`)
| State | Surface |
|---|---|
| Loading | `<p role="status">…</p>` in DocumentList |
| Empty | localised "No documents yet — upload one to get started." |
| Error | `<p role="alert">` with error message |
| Populated | list with status badges + per-doc inline error if `status='failed'` |

## Upload (`Dropzone`)
| State | Surface |
|---|---|
| Idle | drop area with prompt + max-size hint |
| Busy | inline `role="status"` "Uploading and queuing for processing…" |
| Success | **toast.success** "<filename> uploaded — indexing now." |
| Error | inline `role="alert"` AND **toast.error** with message |

## Document viewer (`DocumentViewer` + `useDocumentSource`)
| State | Surface |
|---|---|
| No doc selected | "Pick a document to preview it here." |
| Doc not ready | title + status hint |
| Signed-URL loading | "Loading document…" (`role="status"`) |
| Signed-URL error | `role="alert"` |
| PDF render | react-pdf with built-in loading + error fallbacks |
| Image render | `<img>` with onLoad → bbox overlay |
| Plain-text source | "Plain-text viewer arrives in a later release." (Day 19+ polish) |
| Component crash | wrapped in `<ErrorBoundary>`; chat panel stays alive |

## Chat (`ChatPanel` + `useRag`)
| State | Surface |
|---|---|
| No doc selected | "Pick a ready document to start chatting." |
| Doc not ready | title + status hint |
| Empty | "Ask anything about this document — every answer cites the exact passage." |
| Asking → Streaming | "Thinking…" italic placeholder bubble |
| Done | answer + citations + latency footnote |
| Error | red bubble with `role="alert"` and errorHeading |
| Component crash | wrapped in `<ErrorBoundary>`; viewer stays alive |

## TTS (`NarrateButton`)
| State | Surface |
|---|---|
| Idle | VoicePicker + "Narrate" button |
| Loading | button label "Loading audio…" |
| Playing | `<AudioPlayer>` + per-paragraph highlight + keyboard hint |
| Cached | small "Audio served from cache" badge |
| Fallback engine | small "via Piper fallback" badge |
| Error | inline `role="alert"` next to button |

## Translate (`TranslateMenu`)
| State | Surface |
|---|---|
| Idle | "Translate to…" + 14-option select |
| Busy | inline `role="status"` "Translating…" |
| Done | translated paragraph block under original |
| Cached | "from cache" small label |
| Error | inline `role="alert"` |

## Toasts (Day 19+)
| Variant | Role | Auto-dismiss |
|---|---|---|
| success | `status` | 5 s |
| info | `status` | 5 s |
| error | `alert` | 5 s |

Manual dismiss via × button on each toast (aria-label `Dismiss notification`).

## Error boundaries (Day 19+)
- **Top level** — `main.tsx` wraps `<App />` so a render crash anywhere
  shows the localised fallback instead of a blank page.
- **Per section** — `App.tsx` wraps `<DocumentViewer>` and `<ChatPanel>`
  so a viewer crash leaves chat alive (and vice-versa).
- **Day 22** — `componentDidCatch` reports to Sentry.

## What to add when shipping a new fetch

1. `<LoadingState />` while pending.
2. Empty-state branch using `<EmptyState>` (or local equivalent).
3. Error branch with `role="alert"` for inline + `toast.error()` if action-bound.
4. Wrap any new top-level surface in `<ErrorBoundary>`.
