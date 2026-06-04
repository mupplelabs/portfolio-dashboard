import asyncio
from pydantic_ai import Agent
from pydantic import BaseModel

class MyResult(BaseModel):
    name: str

agent = Agent('test', output_type=MyResult)

async def main():
    result = await agent.run('test')
    print(dir(result))
    print(result.data)

asyncio.run(main())
