from openai import AsyncOpenAI
from app.core.config import settings

# 1. Initialize the official OpenAI client using YOUR secret API key
# Your config.py file automatically pulls this key from the .env file!
client = AsyncOpenAI(api_key=settings.LLM_API_KEY)


# 2. Build a reusable machine to get answers from the AI
async def get_chat_completion(prompt: str, system_instruction: str = "You are a helpful assistant.") -> str:
    """
    A reusable wrapper function. Anyone on the team can pass a question (prompt)
    here, and this function will handle talking to OpenAI and returning the text answer.
    """
    try:
        # We use 'await' because talking to OpenAI over the internet takes a few seconds.
        # This keeps our backend awake and fast while waiting for the response!
        response = await client.chat.completions.create(
            model="gpt-4o-mini", # The fast, cheap hackathon model
            messages=[
                {"role": "system", "content": system_instruction},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3 # Keeps the AI focused and factual (less creative/hallucinatory)
        )
        
        # Extract just the pure text answer from OpenAI's complex JSON packet
        return response.choices[0].message.content
        
    except Exception as e:
        # If OpenAI is down or your API key ran out of money, catch the error cleanly
        return f"LLM Error: Could not retrieve response. Details: {str(e)}"