from agents import ItemHelpers, Runner, gen_trace_id, trace
from email_agent import email_agent
from manager_agent import manager_agent
from writer_agent import ReportData, reset_handoff_report, take_handoff_report

_STATUS_PREFIXES = (
    "Starting research.",
    "Planning searches",
    "Searches planned",
    "Searches complete",
    "Report written",
    "Email sent",
)


def _brief(query: str, clarifications: dict | None = None) -> str:
    parts = [f"Query: {query}"]
    labels = {
        "audience": "Audience and purpose",
        "scope": "Scope and constraints",
        "success": "Success criteria",
    }
    for key, label in labels.items():
        value = ((clarifications or {}).get(key) or "").strip()
        if value:
            parts.append(f"{label}: {value}")
    return "\n".join(parts)


def is_status(text: str) -> bool:
    text = (text or "").strip()
    if not text:
        return True
    return any(text.startswith(prefix) for prefix in _STATUS_PREFIXES)


def _status_for(event) -> str | None:
    if getattr(event, "type", None) == "agent_updated_stream_event":
        name = getattr(event.new_agent, "name", "")
        if name == "Writer Agent":
            return "Searches complete, writing report..."
        if name == "Email Agent":
            return "Report written, sending email..."
        return None

    if getattr(event, "type", None) != "run_item_stream_event":
        return None
    if event.name != "tool_called":
        return None

    tool = getattr(event.item, "tool_name", None) or ""
    if tool == "plan_searches":
        return "Planning searches..."
    if tool == "run_searches":
        return "Searches planned, starting searches..."
    return None


def _parse_report(text: str) -> str | None:
    text = (text or "").strip()
    if not text or is_status(text) or text.lower() == "email sent successfully":
        return None
    try:
        return ReportData.model_validate_json(text).markdown_report
    except Exception:
        start, end = text.find("{"), text.rfind("}")
        if start != -1 and end > start:
            try:
                return ReportData.model_validate_json(text[start : end + 1]).markdown_report
            except Exception:
                return None
    return None


def _report_from_item(item) -> str | None:
    if getattr(item, "type", None) != "message_output_item":
        return None
    text = ItemHelpers.text_message_output(item)
    parsed = _parse_report(text)
    if parsed:
        return parsed
    agent_name = getattr(getattr(item, "agent", None), "name", "")
    if agent_name == "Writer Agent" and text and not is_status(text):
        return text
    return None


def _extract_report(result) -> str:
    stored = take_handoff_report()
    if stored:
        return stored

    if isinstance(result.final_output, ReportData):
        return result.final_output.markdown_report

    for item in reversed(result.new_items):
        parsed = _report_from_item(item)
        if parsed:
            return parsed

    if isinstance(result.final_output, str):
        return _parse_report(result.final_output) or ""
    return ""


class ResearchManager:

    def _brief(self, query: str, clarifications: dict | None = None) -> str:
        return _brief(query, clarifications)

    async def run(self, query: str, clarifications: dict | None = None):
        """Run the manager agent, yielding status updates and the final report."""
        reset_handoff_report()
        trace_id = gen_trace_id()
        brief = self._brief(query, clarifications)
        with trace("Research trace", trace_id=trace_id):
            yield f"Starting research. Trace: https://platform.openai.com/traces/trace?trace_id={trace_id}"
            streamed = Runner.run_streamed(manager_agent, brief, max_turns=20)
            last_status = None
            live_report = ""
            async for event in streamed.stream_events():
                status = _status_for(event)
                if status and status != last_status:
                    last_status = status
                    yield status
                if (
                    getattr(event, "type", None) == "run_item_stream_event"
                    and event.name == "message_output_created"
                ):
                    captured = _report_from_item(event.item)
                    if captured:
                        live_report = captured

            report = live_report or _extract_report(streamed)
            if getattr(streamed.last_agent, "name", "") != "Email Agent" and report:
                yield "Report written, sending email..."
                await Runner.run(email_agent, report)
            yield "Email sent, research complete"
            yield report
