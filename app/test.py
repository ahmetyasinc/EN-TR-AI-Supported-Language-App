from openai import OpenAI
import os

client = OpenAI(
    api_key=os.getenv("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"),
    base_url="https://openrouter.ai/api/v1",
)

resp = client.chat.completions.create(
    model="deepseek/deepseek-r1:free",
    messages=[{"role":"user","content":"Say 'hello' in Turkish, one word."}],
)
print(resp.choices[0].message.content)
