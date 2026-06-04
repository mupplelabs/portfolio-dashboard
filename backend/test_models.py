import asyncio
from pydantic_ai import Agent

async def test_google():
    from pydantic_ai.providers.google import GoogleProvider
    from pydantic_ai.models.google import GoogleModel
    provider = GoogleProvider(api_key="dummy")
    model = GoogleModel("gemini-2.5-flash", provider=provider)
    agent = Agent(model)
    try:
        async with agent.run_stream("test") as result:
            async for chunk in result.stream_text():
                pass
    except Exception as e:
        print(f"Google error: {type(e).__name__}: {e}")

async def main():
    print("Testing Google...")
    await test_google()

if __name__ == "__main__":
    asyncio.run(main())
