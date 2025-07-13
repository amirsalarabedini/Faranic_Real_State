# Research Bot

A research assistant that uses multiple AI agents to conduct comprehensive research on any topic.

## How it works

The research bot uses a multi-agent system to break down research tasks:

1. **Clarifying Agent**: Analyzes user queries to identify ambiguities and determine if clarification is needed before proceeding with research
2. **Planner Agent**: Takes a research query and creates a plan of web searches to perform
3. **Search Agent**: Executes web searches and summarizes the results
4. **Writer Agent**: Synthesizes all search results into a comprehensive report

## Agents

### Clarifying Agent
- **Purpose**: Analyze user queries for clarity and completeness
- **Input**: User research query
- **Output**: Clarification questions (if needed) or improved query
- **Model**: gpt-4o-mini

### Planner Agent
- **Purpose**: Create a strategic plan for web searches
- **Input**: Research query
- **Output**: List of 5-20 search terms with reasoning
- **Model**: o4-mini

### Search Agent
- **Purpose**: Perform web searches and create summaries
- **Input**: Search term and reasoning
- **Output**: 2-3 paragraph summary under 300 words
- **Tools**: Web search tool

### Writer Agent
- **Purpose**: Create comprehensive research reports
- **Input**: Original query and search summaries
- **Output**: Structured markdown report (1000+ words)
- **Model**: gpt-4o-mini

## Usage

```python
from research_bot.manager import ResearchManager

# Run research
manager = ResearchManager()
await manager.run("Your research query here")
```

Or run directly:
```bash
python -m research_bot.main
```
