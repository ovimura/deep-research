import asyncio
import os

from agents import Agent, Runner, function_tool, handoff
from dotenv import load_dotenv

from planner_agent import WebSearchItem, WebSearchPlan, planner_agent
from search_agent import search_agent
from writer_agent import writer_agent

load_dotenv(override=True)
MODEL_NAME = os.getenv("DEFAULT_MODEL_NAME", "gpt-5.4-mini")


async def _plan_output(result) -> str:
    output = result.final_output
    if isinstance(output, WebSearchPlan):
        return output.model_dump_json()
    return str(output)


@function_tool
async def run_searches(plan: WebSearchPlan) -> str:
    """Run every planned web search in parallel and return the summaries.

    Pass the planner output as a WebSearchPlan (the list of search terms and reasons).
    Call this once after plan_searches, not once per term.
    """
    if not plan.searches:
        return "No searches were planned."

    async def _search(item: WebSearchItem) -> str:
        result = await Runner.run(
            search_agent,
            f"Search term: {item.query}\nReason for searching: {item.reason}",
        )
        return result.final_output or ""

    summaries = await asyncio.gather(*[_search(item) for item in plan.searches])
    parts = []
    for item, summary in zip(plan.searches, summaries):
        parts.append(f"Search: {item.query}\nReason: {item.reason}\nSummary: {summary}")
    return "\n\n".join(parts)


INSTRUCTIONS = """
You orchestrate deep research. You receive a query and optional clarifications
(audience, scope, success criteria).

1. Call plan_searches with the FULL user message. Do not drop clarifications.
2. Call run_searches once with that plan. Do not search term-by-term yourself.
3. Handoff to the Writer Agent with the original brief and the search summaries.
   Do not write the report or send email yourself.

Never call run_searches before you have a plan.
"""

manager_agent = Agent(
    name="Research Manager",
    instructions=INSTRUCTIONS,
    model=MODEL_NAME,
    tools=[
        planner_agent.as_tool(
            tool_name="plan_searches",
            tool_description="Produce a list of web searches from the research brief.",
            custom_output_extractor=_plan_output,
        ),
        run_searches,
    ],
    handoffs=[
        handoff(
            writer_agent,
            tool_description_override=(
                "Hand off the brief and search summaries so the Writer Agent can "
                "produce the final report and deliver it."
            ),
        )
    ],
)
