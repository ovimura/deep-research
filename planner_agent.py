from pydantic import BaseModel, Field
from agents import Agent
import os
from dotenv import load_dotenv
load_dotenv(override=True)

MODEL_NAME = os.getenv("DEFAULT_MODEL_NAME", "gpt-5.4-mini")
HOW_MANY_SEARCHES = int(os.getenv("HOW_MANY_SEARCHES", 5))


INSTRUCTIONS = f"""
You are a research assistant. Given a user query and optional clarifications
(audience, scope, success criteria), come up with a set of web searches
to perform to best answer the query under those constraints.
Output {HOW_MANY_SEARCHES} terms to query for.
"""

class WebSearchItem(BaseModel):
    reason: str = Field(description="Your reasoning for why this search is important to the query.")
    query: str = Field(description="The search term to use for the web search.")


class WebSearchPlan(BaseModel):
    searches: list[WebSearchItem] = Field(description="A list of web searches to perform to best answer the query.")
    
planner_agent = Agent(name="Planner Agent", instructions=INSTRUCTIONS, model=MODEL_NAME, output_type=WebSearchPlan)