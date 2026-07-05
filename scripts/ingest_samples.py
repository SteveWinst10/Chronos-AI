import os
import sys

# Manually load .env
def load_env():
    env_path = os.path.join(os.getcwd(), ".env")
    if os.path.exists(env_path):
        with open(env_path, "r") as f:
            for line in f:
                if "=" in line and not line.startswith("#"):
                    key, value = line.strip().split("=", 1)
                    os.environ[key] = value

load_env()

import asyncio
import cognee

async def ingest_samples():
    samples = [
        {"title": "OpenAI announces GPT-5 development", "content": "OpenAI has officially started working on GPT-5, promising major reasoning improvements.", "source": "Reuters", "link": "https://reuters.com/gpt5"},
        {"title": "Microsoft expands OpenAI partnership", "content": "Microsoft is investing another $10 billion to scale OpenAI's supercomputing needs.", "source": "Bloomberg", "link": "https://bloomberg.com/ms-openai"},
        {"title": "NVIDIA launches new AI chips for LLMs", "content": "NVIDIA revealed the Blackwell B200 GPU, designed specifically for training next-gen models like GPT-5.", "source": "TechCrunch", "link": "https://techcrunch.com/nvidia-blackwell"},
        {"title": "Anthropic releases Claude 4", "content": "Anthropic's latest model Claude 4 achieves state-of-the-art results in coding and logic.", "source": "The Verge", "link": "https://theverge.com/claude4"}
    ]
    
    print("Ingesting sample news into Cognee...")
    for s in samples:
        payload = f"Title: {s['title']}\nSource: {s['source']}\nLink: {s['link']}\nContent: {s['content']}"
        await cognee.remember(payload, dataset_name="news")
    
    print("Running cognify...")
    await cognee.cognify()
    print("Ingestion complete.")

if __name__ == "__main__":
    asyncio.run(ingest_samples())
