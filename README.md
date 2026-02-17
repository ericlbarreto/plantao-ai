# Plantão AI

AI-powered shift-offer analyser for doctors.  
Receives WhatsApp messages, decides if it's a shift offer and whether the doctor can accept it.

## Stack

- **FastAPI** – async web framework
- **Agno** – AI agent orchestration (Skills + Workflow)
- **SQLAlchemy 2.0** – async ORM (SQLite by default)
- **OpenTelemetry** – tracing via OTLP to LangSmith
- **uv** – Python package manager

## Setup

```bash
# 1. Install dependencies
uv sync

# 2. Create .env
cp .env.example .env
# Edit .env with your OPENAI_API_KEY

# 3. Run the server
uv run uvicorn app.main:app --reload --port 8000
```

API docs: <http://localhost:8000/docs>

## Test with curl

### Register a doctor

```bash
curl -s -X POST http://localhost:8000/schedule/doctor \
  -H "Content-Type: application/json" \
  -d '{"name":"Dr. Silva","phone":"+5511999999999"}'
```

### Add weekly availability (Monday 07:00–19:00)

```bash
curl -s -X POST http://localhost:8000/schedule/availability \
  -H "Content-Type: application/json" \
  -d '{"doctor_id":1,"weekday":0,"start_time":"07:00","end_time":"19:00"}'
```

### Add one-off busy slot

```bash
curl -s -X POST http://localhost:8000/schedule/busy \
  -H "Content-Type: application/json" \
  -d '{"doctor_id":1,"start_dt":"2026-02-23T08:00:00","end_dt":"2026-02-23T10:00:00","reason":"Consulta"}'
```

### Add recurring busy rule (lunch every Monday)

```bash
curl -s -X POST http://localhost:8000/schedule/recurring-busy \
  -H "Content-Type: application/json" \
  -d '{"doctor_id":1,"weekday":0,"start_time":"12:00","end_time":"13:00","label":"Almoço"}'
```

### Process a WhatsApp message

```bash
curl -s -X POST http://localhost:8000/message \
  -H "Content-Type: application/json" \
  -d '{"phone":"+5511999999999","text":"Oi! Plantão diurno segunda 24/02, aceita?"}'
```

## Project Structure

```
app/
  main.py                          # FastAPI app + lifespan
  common/
    config.py                      # pydantic-settings (.env)
    tracing.py                     # OpenTelemetry setup
  db/
    session.py                     # Async SQLAlchemy engine
    models.py                      # Doctor, AvailabilityRule, BusySlot, RecurringBusyRule
  api/controllers/
    message_controller.py          # POST /message
    schedule_controller.py         # POST /schedule/*
  ai/
    schemas.py                     # Pydantic models (MessageIn, OfferExtraction, etc.)
    tools/
      schedule_tool.py             # Deterministic schedule checker
      whatsapp_tool.py             # TODO placeholder
    skills/
      offer_extraction/            # LLM skill → OfferExtraction
      schedule_check/              # Deterministic skill → [ShiftValidation]
      decision/                    # LLM skill → DecisionOut
    workflows/
      shift_offer_workflow.py      # Chains the 3 skills
```
