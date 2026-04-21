"""
This is an example of how to use the OlostepTools.

Prerequisites:
- Install the SDK: `pip install olostep` (requires Python >= 3.11)
- Create an Olostep account and get an API key: https://olostep.com
- Set the API key as an environment variable:
    export OLOSTEP_API_KEY=<your-api-key>
"""

from agno.agent import Agent
from agno.tools.olostep import OlostepTools

agent = Agent(
    tools=[
        OlostepTools(
            enable_scrape=True,
            enable_answers=True,
            enable_map=True,
        )
    ],
    markdown=True,
)

if __name__ == "__main__":
    # Should use answers (AI web research)
    agent.print_response(
        "Find the latest news on 'web scraping technologies' and summarize it."
    )

    # Should use scrape
    agent.print_response("Summarize this page: https://docs.agno.com/introduction/")
