---
title: deep_research
app_file: app.py
sdk: gradio
sdk_version: 6.14.0
---

# Deep Research

A Gradio app that turns a research question into a structured report. It plans web searches, gathers sources in parallel, writes a long-form markdown report, and optionally delivers the result by email or push notification.

## Design

`app.py` is the UI. It hands each query to `ResearchManager`, which runs a four-step pipeline of OpenAI Agents SDK agents:

1. **Planner** (`planner_agent.py`) — produces a list of search terms for the query.
2. **Search** (`search_agent.py`) — runs each term with the web search tool and returns a short summary. Searches execute concurrently.
3. **Writer** (`writer_agent.py`) — synthesizes the summaries into a detailed markdown report.
4. **Delivery** (`email_agent.py`, `messenger.py`) — sends the report by SMTP email, or via Pushover if email is disabled.

Status updates stream back to the UI as each stage completes.

## Environment variables

Load from a `.env` file in the project root.

| Variable | Required | Description |
| --- | --- | --- |
| `OPENAI_API_KEY` | Yes | OpenAI API key used by the Agents SDK. |
| `DEFAULT_MODEL_NAME` | No | Model for all agents. Defaults to `gpt-5.4-mini`. |
| `HOW_MANY_SEARCHES` | No | Number of search terms the planner should produce. Defaults to `5`. |
| `USE_EMAIL` | No | `true` (default) sends via SMTP; `false` sends a Pushover notification instead. |
| `EMAIL_ADDRESS` | If email | SMTP username and recipient (mail is sent to this address). |
| `EMAIL_SMTP_SERVER` | If email | SMTP host (port 587, STARTTLS). |
| `EMAIL_APP_PASSWORD` | If email | SMTP password or app password. |
| `PUSHOVER_USER` | If push | Pushover user key. |
| `PUSHOVER_TOKEN` | If push | Pushover application token. |

## Install & Run locally

```bash
pip install -r requirements.txt
python app.py
```
