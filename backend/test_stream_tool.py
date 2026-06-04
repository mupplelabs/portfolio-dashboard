import asyncio
from pydantic_ai import Agent, RunContext

agent = Agent('test')

@agent.tool
def fake_tool(ctx: RunContext) -> str:
    print("FAKE TOOL CALLED")
    return "Some data"

async def main():
    print("Starting stream...")
    try:
        async with agent.run_stream("call the tool") as result:
            async for chunk in result.stream_text(delta=True):
                print(f"CHUNK: {chunk}")
    except Exception as e:
        print(f"ERROR: {e}")
    print("Done stream.")

if __name__ == "__main__":
    asyncio.run(main())
