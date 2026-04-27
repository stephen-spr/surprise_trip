from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task
from crewai_tools import SerperDevTool, ScrapeWebsiteTool
from pydantic import BaseModel, Field
from typing import List, Optional
import re
import os

# ✅ Resolve absolute paths (FIX for Docker)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# ✅ Load API key
SERPER_API_KEY = os.getenv("SERPER_API_KEY")

# ✅ Create tools once (reuse)
search_tool = SerperDevTool(api_key=SERPER_API_KEY)
scrape_tool = ScrapeWebsiteTool()


def filter_malicious_snippets(prompt: str) -> str:
    harmful_patterns = [
        r'\b(?:malicious|harmful|dangerous|unsafe)\b',
        r'\b(?:drop|delete|truncate|alter|insert)\b',
    ]
    for pattern in harmful_patterns:
        if re.search(pattern, prompt, re.IGNORECASE):
            raise ValueError("Potentially harmful snippet detected in prompt.")
    return prompt


def sanitize_prompt(prompt: str) -> str:
    if re.search(r'\b(?:execute|run|command|script|eval|system)\b', prompt, re.IGNORECASE):
        raise ValueError("Potentially harmful command detected in prompt.")
    return prompt


class Activity(BaseModel):
    name: str
    location: str
    description: str
    date: str
    cousine: str
    why_its_suitable: str
    reviews: Optional[List[str]]
    rating: Optional[float]


class DayPlan(BaseModel):
    date: str
    activities: List[Activity]
    restaurants: List[str]
    flight: Optional[str] = None


class Itinerary(BaseModel):
    name: str
    day_plans: List[DayPlan]
    hotel: str


@CrewBase
class SurpriseTravelCrew():
    # ✅ FIX: absolute paths
    agents_config = os.path.join(BASE_DIR, "config/agents.yaml")
    tasks_config = os.path.join(BASE_DIR, "config/tasks.yaml")

    @agent
    def personalized_activity_planner(self) -> Agent:
        return Agent(
            config=self.agents_config['personalized_activity_planner'],
            tools=[search_tool, scrape_tool],
            verbose=True,
            allow_delegation=False,
        )

    @agent
    def restaurant_scout(self) -> Agent:
        sanitize_prompt(str(self.agents_config['restaurant_scout']))
        return Agent(
            config=self.agents_config['restaurant_scout'],
            tools=[search_tool, scrape_tool],
            verbose=True,
            allow_delegation=False,
        )

    @agent
    def itinerary_compiler(self) -> Agent:
        return Agent(
            config=self.agents_config['itinerary_compiler'],
            tools=[search_tool],
            verbose=True,
            allow_delegation=False,
        )

    @task
    def personalized_activity_planning_task(self) -> Task:
        return Task(
            config=self.tasks_config['personalized_activity_planning_task'],
            agent=self.personalized_activity_planner()
        )

    @task
    def restaurant_scenic_location_scout_task(self) -> Task:
        return Task(
            config=self.tasks_config['restaurant_scenic_location_scout_task'],
            agent=self.restaurant_scout()
        )

    @task
    def itinerary_compilation_task(self) -> Task:
        return Task(
            config=self.tasks_config['itinerary_compilation_task'],
            agent=self.itinerary_compiler(),
            output_json=Itinerary
        )

    @crew
    def crew(self) -> Crew:
        return Crew(
            agents=self.agents,
            tasks=self.tasks,
            process=Process.sequential,
            verbose=True,
            # process=Process.hierarchical, # In case you want to use that instead https://docs.crewai.com/how-to/Hierarchical/
        )
