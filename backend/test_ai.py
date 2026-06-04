import asyncio
from pydantic_ai import Agent

async def main():
    agent = Agent('test')
    res = await agent.run('Hello')
    print("OUTPUT:", res.output)

asyncio.run(main())
