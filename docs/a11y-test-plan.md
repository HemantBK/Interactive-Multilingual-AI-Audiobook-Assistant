# Accessibility test plan

Build plan §23 targets WCAG 2.1 AA. axe-core in CI catches automated
issues; this plan covers the manual scenarios CI can't verify (screen
reader announcements, focus order, keyboard-only operation).

Run before launch (Day 28) and after any major UI change.

## Tools

| Tool | Platform | When |
|---|---|---|
| **NVDA** + Firefox | Windows 10/11 | Primary — most common Indic-screen-reader combination |
| VoiceOver | macOS Safari | Secondary — second-largest user base |
| **axe DevTools** browser extension | Chromium | Spot-check during development |
| Keyboard only (no mouse) | any | After every UI change |
| Tab key + Shift+Tab | any | Focus-order verification |

## Setup

1. Install NVDA from nvaccess.org (free).
2. Start NVDA before opening the browser. NVDA reads what the browser focuses.
3. Use Firefox — best NVDA integration.
4. Set NVDA speech rate moderate so you can keep up with announcements.

## Test scenarios

### 1. Sign-in flow (unauth)

- [ ] Tab once from page load — focus lands on **skip link** ("Skip to main content"). NVDA announces "Skip to main content, link".
- [ ] Tab again — focus moves to language switcher. NVDA: "Language, combo box, English".
- [ ] Change language to Hindi (Alt+Down arrow on combobox). NVDA: "हिन्दी selected".
- [ ] After language change, the page should re-read in Hindi (NVDA may need a refresh; document language is set on `<html lang>`).
- [ ] Tab to email input. NVDA: "Email me a magic link, edit, required".
- [ ] Tab to "Sign in" button. NVDA: "Sign in, button".
- [ ] Submit empty form. Native HTML5 validation blocks; NVDA announces required-field error.

### 2. Authenticated layout

- [ ] After login, focus stays where the auth callback dropped you. NVDA reads the upload region first.
- [ ] Tab order: skip link → language → sign-out → upload region → file input → documents list buttons → viewer (or pickDocument hint) → chat input.
- [ ] No focus traps. Shift+Tab walks back through the same order.

### 3. Upload + indexing

- [ ] Tab to file input. NVDA: "Choose a file to upload, file upload".
- [ ] Press Enter or Space — file picker opens.
- [ ] Pick a PDF. NVDA announces upload status ("Uploading and queuing for processing…").
- [ ] On success, **toast** appears top-right. NVDA reads it because role="status".
- [ ] Tab back to documents list — new doc appears at top with status badge.
- [ ] Wait for status → "Processing" → "Ready". Polling re-renders the list; NVDA does NOT announce on each poll (polling component has no live region — desired, otherwise it'd be noisy).

### 4. Pick a document

- [ ] Tab through document list buttons. NVDA: "Document title, button, pressed=false". When focused on the selected doc: "pressed=true".
- [ ] Press Enter / Space — doc selected. Viewer + chat populate.
- [ ] **Confirm**: lang attribute on the viewer/chat reflects the doc's source language. For a Hindi PDF, NVDA pronounces in Hindi.

### 5. Ask a question (RAG)

- [ ] Tab to question textarea. NVDA: "Question, edit text".
- [ ] Type a question. Press Enter (NOT Shift+Enter) → submit.
- [ ] NVDA announces "Thinking…" (status role).
- [ ] When answer arrives, NVDA reads the answer paragraph by paragraph because the message log is `aria-live="polite"`.
- [ ] **Confirm**: answer in document's language is announced in that language (per-content `lang` attribute set in MessageList).
- [ ] Tab to citations. NVDA: "Jump to page 12 and highlight passage, button".
- [ ] Press Enter on citation. Document viewer scrolls to page 12. (Visual highlight; NVDA users won't see bbox but the page change is implied via scroll.)

### 6. Translate the answer

- [ ] Tab to the per-message "Translate to…" select. NVDA: "Translate this answer, combo box".
- [ ] Pick "हिन्दी". NVDA: "Translating…" then translation announced.
- [ ] **Confirm**: translation has lang="hi" so NVDA pronounces correctly.

### 7. Narrate the answer

- [ ] Before clicking Narrate: tab to voice picker. NVDA: "Choose voice, combo box, English — Aria".
- [ ] Pick a different voice. NVDA confirms.
- [ ] Tab to "Narrate" button. NVDA: "Narrate this answer, button".
- [ ] Click. Player appears with autoplay.
- [ ] **Keyboard test** — focus the player region (tabIndex=0) and press:
  - [ ] Space → pause/play (NVDA may announce focus to native controls)
  - [ ] ←/→ → seek 5s (no audible cue beyond audio time change)
  - [ ] ↑/↓ → volume (system volume indicator)
  - [ ] M → mute toggle
  - [ ] 0 → restart
- [ ] When audio plays, paragraph highlight follows. NVDA may or may not re-announce — this is visual feedback, not announced.

### 8. Sign out

- [ ] Tab to "Sign out" in header. NVDA: "Sign out, button".
- [ ] Click. App returns to sign-in form. NVDA reads new heading.

### 9. Error scenarios (induced)

- [ ] Disable network mid-question. NVDA announces error bubble (role="alert" interrupts).
- [ ] Toast also fires; NVDA reads it.
- [ ] After reconnect, retry works.

### 10. KILL_SWITCH active

- [ ] Operator sets `KILL_SWITCH=true`. Asking a question returns 503.
- [ ] Frontend renders a friendly error in the chat bubble + toast.
- [ ] NVDA announces both.

## Pass criteria

- All scenarios completable using **keyboard only**.
- All errors announced with role="alert" or via toast.
- All status changes announced via role="status" or `aria-live="polite"`.
- No focus traps; Shift+Tab always retraces.
- No content unreadable by NVDA (e.g. icon-only buttons all have `aria-label`).
- axe DevTools scan: 0 critical, 0 serious issues. Moderate issues triaged in `docs/dogfood-log.md`.

## Sign-off

Manual NVDA pass: ☐ &nbsp; date / runner: __________
Manual VoiceOver pass: ☐ &nbsp; date / runner: __________
axe-core CI green for 7 days: ☐
