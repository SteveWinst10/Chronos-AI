import os
from openai import OpenAI

def load_openai_key():
    env_path = os.path.join(os.getcwd(), ".env")
    if os.path.exists(env_path):
        with open(env_path, "r") as f:
            for line in f:
                if "OPENAI_API_KEY=" in line:
                    return line.strip().split("=", 1)[1]
    return os.environ.get("OPENAI_API_KEY")

def test_api_key():
    api_key = load_openai_key()
    if not api_key:
        print("Error: OPENAI_API_KEY not found.")
        return

    client = OpenAI(api_key=api_key)
    
    # Try multiple models to be sure
    for model in ["gpt-4o-mini", "gpt-3.5-turbo"]:
        print(f"Testing model {model}...")
        try:
            response = client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": "hi"}],
                max_tokens=5
            )
            print(f"SUCCESS with {model}: {response.choices[0].message.content}")
            return
        except Exception as e:
            print(f"FAILED with {model}: {e}")

if __name__ == "__main__":
    test_api_key()
