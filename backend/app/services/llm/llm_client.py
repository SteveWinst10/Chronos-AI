import logging
import hashlib
import random
from typing import AsyncIterator, Optional
from openai import AsyncOpenAI
from app.core.config import settings

logger = logging.getLogger(__name__)

class LLMClient:
    def __init__(self, api_key: Optional[str] = None):
        # Allow passing an API key, otherwise pull from config
        self.api_key = api_key or settings.effective_llm_api_key
        # Check if the key is a dummy or not set
        is_dummy_key = not self.api_key or "change-me" in self.api_key or "dummy" in self.api_key
        
        if is_dummy_key:
            # We initialize the client with a dummy string if no real key is set to prevent errors on init
            self.client = AsyncOpenAI(api_key="dummy-key")
            self.has_valid_key = False
        else:
            self.client = AsyncOpenAI(api_key=self.api_key)
            self.has_valid_key = True
            
        self.model = "gpt-4o-mini"

    async def generate_stream(self, prompt: str, system_prompt: str) -> AsyncIterator[str]:
        """Stream chunks of response from the LLM."""
        if not self.has_valid_key:
            # Fallback mock generator
            mock_resp = f"[MOCK LLM STREAM RESPONSE FOR PROMPT: {prompt[:30]}...]"
            for char in mock_resp:
                yield char
            return

        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                stream=True
            )
            async for chunk in response:
                content = chunk.choices[0].delta.content
                if content:
                    yield content
        except Exception as e:
            logger.error(f"Error in LLM Client generate_stream: {e}")
            yield f"LLM Error: {str(e)}"

    async def get_completion(self, prompt: str, system_prompt: str) -> str:
        """Get the full completion response from the LLM."""
        if not self.has_valid_key:
            # Mock extraction or consolidation output for test safety
            if "knowledge graph extraction" in system_prompt.lower():
                return '[]'
            elif "graph optimizer" in system_prompt.lower():
                return '[]'
            return f"[MOCK LLM RESPONSE FOR PROMPT: {prompt[:30]}]"

        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3
            )
            return response.choices[0].message.content or ""
        except Exception as e:
            logger.error(f"Error in LLM Client get_completion: {e}")
            return f"LLM Error: {str(e)}"

    async def get_embedding(self, text: str) -> list[float]:
        """Generate a dense vector representation of the text. Falls back to deterministic mock if no key is set."""
        dim = 1536
        if not self.has_valid_key:
            return self._generate_deterministic_mock_embedding(text, dim)

        try:
            response = await self.client.embeddings.create(
                model="text-embedding-3-small",
                input=text
            )
            return response.data[0].embedding
        except Exception as e:
            logger.warning(f"Failed to generate embedding via OpenAI: {e}. Falling back to deterministic mock.")
            return self._generate_deterministic_mock_embedding(text, dim)

    def _generate_deterministic_mock_embedding(self, text: str, dim: int) -> list[float]:
        """Generate a stable, deterministic normalized mock embedding for the given text."""
        h = hashlib.sha256(text.encode('utf-8')).digest()
        rng = random.Random(int.from_bytes(h, 'big'))
        emb = [rng.gauss(0.0, 1.0) for _ in range(dim)]
        # Normalize vector
        norm = sum(x**2 for x in emb)**0.5
        if norm > 0:
            emb = [x/norm for x in emb]
        return emb


# Re-expose package-level function for backward compatibility
async def get_chat_completion(prompt: str, system_instruction: str = "You are a helpful assistant.") -> str:
    """Wrapper function delegating to the new LLMClient class."""
    client = LLMClient()
    return await client.get_completion(prompt, system_instruction)