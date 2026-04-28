from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task
from crewai_tools import SerperDevTool, ScrapeWebsiteTool
from pydantic import BaseModel, Field
from typing import List, Optional
import re
from urllib.parse import urlparse
import ipaddress

def filter_malicious_snippets(prompt: str) -> str:
    '''Sanitize the prompt to filter out malicious snippets.'''
    harmful_patterns = [
        r'\b(?:malicious|harmful|dangerous|unsafe)\b',
        r'\b(?:drop|delete|truncate|alter|insert)\b',
    ]
    for pattern in harmful_patterns:
        if re.search(pattern, prompt, re.IGNORECASE):
            raise ValueError("Potentially harmful snippet detected in prompt.")
    return prompt

def sanitize_prompt(prompt: str) -> str:
    '''Filter the prompt to prevent indirect prompt injection.'''
    if re.search(r'\b(?:execute|run|command|script|eval|system)\b', prompt, re.IGNORECASE):
        raise ValueError("Potentially harmful command detected in prompt.")
    return prompt

def validate_user_input(user_input: str) -> str:
    '''Validate user input to prevent prompt injection.'''
    if len(user_input) > 2000:
        raise ValueError("Input exceeds maximum length of 2000 characters.")
    return filter_malicious_snippets(user_input)

def sanitize_url(url: str) -> str:
    '''Validate and sanitize URL to prevent SSRF.'''
    parsed = urlparse(url)
    
    if parsed.scheme not in ('http', 'https'):
        raise ValueError(f"Invalid URL scheme: {parsed.scheme}")
    
    hostname = parsed.hostname or ''
    if hostname in ('localhost', '127.0.0.1', '0.0.0.0', '169.254.169.254'):
        raise ValueError("Access to private/local addresses blocked")
    
    try:
        ip = ipaddress.ip_address(hostname)
        if ip.is_private or ip.is_loopback or ip.is_link_local:
            raise ValueError("Access to private IP ranges blocked")
    except ValueError:
        pass
    
    allowed_domains = ['example.com', 'api.example.com']  # Configure as needed
    if allowed_domains and not any(hostname.endswith(d) for d in allowed_domains):
        raise ValueError(f"Domain not in allowlist: {hostname}")
    
    return url

class Activity(BaseModel):
    name: str = Field(..., description="Name of the activity")
    location: str = Field(..., description="Location of the activity")
    description: str = Field(..., description="Description of the activity")
    date: str = Field(..., description="Date of the activity")
    cousine: str = Field(..., description="Cousine of the restaurant")
    why_its_suitable: str = Field(..., description="Why it's suitable for the traveler")
    reviews: Optional[List[str]] = Field(..., description="List of reviews")
    rating: Optional[float] = Field(..., description="Rating of the activity")

class DayPlan(BaseModel):
    date: str = Field(..., description="Date of the day")
    activities: List[Activity] = Field(..., description="List of activities")
    restaurants: List[str] = Field(..., description="List of restaurants")
    flight: Optional[str] = Field(None, description="Flight information")

class Itinerary(BaseModel):
    name: str = Field(..., description="Name of the itinerary, something funny")
    day_plans: List[DayPlan] = Field(..., description="List of day plans")
    hotel: str = Field(..., description="Hotel information")

@CrewBase
class SurpriseTravelCrew():
    """SurpriseTravel crew"""
    agents_config = 'config/agents.yaml'
    tasks_config = 'config/tasks.yaml'

    @agent
    def personalized_activity_planner(self) -> Agent:
        return Agent(
            config=self.agents_config['personalized_activity_planner'],
            tools=[SerperDevTool(), ScrapeWebsiteTool()],
            verbose=True,
            allow_delegation=False,
        )

    @agent
    def restaurant_scout(self) -> Agent:
        sanitized_config = sanitize_prompt(str(self.agents_config['restaurant_scout']))
        return Agent(
            config=sanitized_config,
            tools=[SerperDevTool(), ScrapeWebsiteTool()],
            verbose=True,
            allow_delegation=False,
        )

    @agent
    def itinerary_compiler(self) -> Agent:
        return Agent(
            config=self.agents_config['itinerary_compiler'],
            tools=[SerperDevTool()],
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
        """Creates the SurpriseTravel crew"""
        return Crew(
            agents=self.agents,
            tasks=self.tasks,
            process=Process.sequential,
            verbose=True,
        )