import asyncio
import os
import cognee

async def test_cognee():
    os.environ["OPENAI_API_KEY"] = "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"
    
    print("Testing Cognee recall...")
    try:
        results = await cognee.recall("AI news")
        print(f"Results: {results}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_cognee())
