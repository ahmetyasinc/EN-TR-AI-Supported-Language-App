# openrouter_test.py
import os
from openai import OpenAI

API_KEY = os.getenv("OPENROUTER_API_KEY")
assert API_KEY, "OPENROUTER_API_KEY ortam değişkenini ayarlayın."

client = OpenAI(
    api_key=API_KEY,
    base_url="https://openrouter.ai/api/v1",
)

resp = client.chat.completions.create(
    model="deepseek/deepseek-r1:free",
    # attribution isteğe bağlı:
    extra_headers={
        # "HTTP-Referer": "https://senin-uygulaman.com",
        # "X-Title": "EN-TR Vocab App",
    },
    messages=[
        {"role": "system", "content": "Reply briefly."},
        {"role": "user", "content": "Türkçe tek kelimeyle selam ver."},
    ],
)

print("MODEL:", resp.model)
print("REPLY:", resp.choices[0].message.content.strip())
