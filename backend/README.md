---
title: Interactive Audiobook-Assistant API
emoji: 📚
colorFrom: orange
colorTo: yellow
sdk: docker
app_port: 7860
pinned: false
license: apache-2.0
---

# Interactive Audiobook-Assistant — backend

FastAPI backend for Interactive Audiobook-Assistant. Deploys to **Hugging Face Spaces** (Docker SDK) and runs locally against the same image.

The YAML block above is read by Hugging Face Spaces to configure this Space. It is ignored by GitHub's Markdown renderer (rendered as page metadata).

## Local development

```bash
# from repo root
cd backend

# create venv
python -m venv .venv
# Windows: .venv\Scripts\activate
source .venv/bin/activate

# install deps
pip install -r requirements.txt

# copy env template
cp ../.env.example ../.env
# edit ../.env with your Supabase + Gemini keys

# run
uvicorn app.main:app --reload --port 7860
```

Then open http://localhost:7860/health — expect `{"status":"ok",...}`.

## Deploy to Hugging Face Spaces

See `infra/hf-space/README.md`.

## Project layout

```
backend/
├── app/
│   ├── api/          # HTTP route handlers
│   ├── core/         # config, security, rate limiting
│   ├── db/           # Supabase client, migrations glue
│   ├── models/       # Pydantic schemas
│   ├── services/     # business logic (OCR, RAG, TTS, translate, safety)
│   └── main.py       # FastAPI app
├── tests/
├── Dockerfile        # → Hugging Face Space
├── pyproject.toml
└── requirements.txt
```
