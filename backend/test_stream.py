import asyncio
from pydantic_ai import Agent
from pydantic_ai.models.test import TestModel

agent = Agent(TestModel())

@agent.tool
def get_weather(ctx, location: str) -> str:
    print("Tool called")
    return "Sunny"

async def main():
    async with agent.run_stream("What is the weather in Paris?") as result:
        async for event in result.stream():
            print(event)

if __name__ == "__main__":
    asyncio.run(main())
