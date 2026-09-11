from agents import Runner, trace, gen_trace_id
from search_agent import search_agent
from planner_agent import planner_agent, WebSearchItem, WebSearchPlan
from writer_agent import writer_agent, ReportData
from email_agent import email_agent
import asyncio

class ResearchManager:

    def _brief(self, query: str, clarifications: dict | None = None) -> str:
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

    async def run(self, query: str, clarifications: dict | None = None):
        """ Run the deep research process, yielding the status updates and the final report"""
        trace_id = gen_trace_id()
        brief = self._brief(query, clarifications)
        with trace("Research trace", trace_id=trace_id):
            yield f"Starting research. Trace: https://platform.openai.com/traces/trace?trace_id={trace_id}"
            search_plan = await self.plan_searches(brief)
            yield f"Searches planned, starting {len(search_plan.searches)} searches..."     
            search_results = await self.perform_searches(search_plan)
            yield "Searches complete, writing report..."
            report = await self.write_report(brief, search_results)
            yield "Report written, sending email..."
            await self.send_email(report)
            yield "Email sent, research complete"
            yield report.markdown_report

    async def plan_searches(self, brief: str) -> WebSearchPlan:
        """ Plan the searches to perform for the query """
        result = await Runner.run(planner_agent, brief)
        return result.final_output

    async def perform_searches(self, search_plan: WebSearchPlan) -> list[str]:
        """ Perform the searches to perform for the query """
        tasks = [self.search(item) for item in search_plan.searches]
        return await asyncio.gather(*tasks)

    async def search(self, item: WebSearchItem) -> str | None:
        """ Perform a search for the query """
        input_message = f"Search term: {item.query}\nReason for searching: {item.reason}"
        result = await Runner.run(search_agent, input_message)
        return result.final_output

    async def write_report(self, brief: str, search_results: list[str]) -> ReportData:
        """ Write the report for the query """
        input_message = f"{brief}\nSummarized search results: {search_results}"
        result = await Runner.run(writer_agent, input_message)
        return result.final_output
    
    async def send_email(self, report: ReportData) -> None:
        await Runner.run(email_agent, report.markdown_report)