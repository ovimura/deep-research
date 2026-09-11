from contextvars import ContextVar

from pydantic import BaseModel, Field
from agents import Agent, handoff
from dotenv import load_dotenv
import os

from email_agent import email_agent

load_dotenv(override=True)
MODEL_NAME = os.getenv("DEFAULT_MODEL_NAME", "gpt-5.4-mini")

_handoff_report: ContextVar[str] = ContextVar("handoff_report", default="")


class ReportData(BaseModel):
    short_summary: str = Field(description="A short 2-3 sentence summary of the findings.")
    markdown_report: str = Field(description="The final report")
    follow_up_questions: list[str] = Field(description="Suggested topics to research further")


def store_handoff_report(_ctx, report: ReportData) -> None:
    _handoff_report.set(report.markdown_report)


def take_handoff_report() -> str:
    return _handoff_report.get()


def reset_handoff_report() -> None:
    _handoff_report.set("")


INSTRUCTIONS = """
You are a senior researcher tasked with writing a cohesive report for a research query.
You will be provided with the original query, optional clarifications (audience, scope,
and success criteria), and some research.
Generate a comprehensive report based on the research, the query, and any clarifications.
Honor the requested audience, scope, and success criteria when they are present.
The final output should be in markdown format, and it should be lengthy and detailed. Aim 
for 5-10 pages of content, at least 1000 words.

After the report is complete, you MUST hand off to the Email Agent. When you hand off,
pass the full report object (short_summary, markdown_report, follow_up_questions).
Do not mention the handoff in the report itself.
"""


writer_agent = Agent(
    name="Writer Agent",
    instructions=INSTRUCTIONS,
    model=MODEL_NAME,
    output_type=ReportData,
    handoffs=[
        handoff(
            email_agent,
            input_type=ReportData,
            on_handoff=store_handoff_report,
            tool_description_override=(
                "Deliver the finished report by email, or by push if email is disabled. "
                "Pass the full ReportData object as the handoff input."
            ),
        )
    ],
)
