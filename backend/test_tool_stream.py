import asyncio
from pydantic_ai import Agent

agent = Agent("test")

@agent.tool
def test_tool(ctx) -> str:
    print("Tool called!")
    return "Tool result: 42"

async def test_anthropic():
    from pydantic_ai.providers.anthropic import AnthropicProvider
    from pydantic_ai.models.anthropic import AnthropicModel
    import os
    
    # We need a real API key for Claude to test this. 
    # Or we can just inspect the code of stream_text.
    pass
