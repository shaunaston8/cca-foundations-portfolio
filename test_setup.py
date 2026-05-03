import os
from dotenv import load_dotenv
from anthropic import Anthropic

load_dotenv()

client = Anthropic()  # automatically reads ANTHROPIC_API_KEY from environment

response = client.messages.create(
    model="claude-opus-4-5",
    max_tokens=100,
    messages=[
        {"role": "user", "content": "Reply with exactly: 'Setup confirmed.'"}
    ],
)

print(response.content[0].text)