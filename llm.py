"""Thin wrapper around the OpenAI chat API.

The model is fixed to gpt-3.5-turbo per the assignment instructions. The only
additions over the original skeleton are an optional `system` message (for
role/persona steering) and a per-call `temperature` so the storyteller can run
hot (creative) while the judges run cold (consistent).
"""
import os

import openai
from dotenv import load_dotenv

load_dotenv()

MODEL = "gpt-3.5-turbo"  # Do not change (assignment constraint).


def call_model(
    prompt: str,
    system: str | None = None,
    max_tokens: int = 3000,
    temperature: float = 0.1,
) -> str:
    openai.api_key = os.getenv("OPENAI_API_KEY")  # please use your own openai api key here.

    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    resp = openai.ChatCompletion.create(
        model=MODEL,
        messages=messages,
        stream=False,
        max_tokens=max_tokens,
        temperature=temperature,
    )
    return resp.choices[0].message["content"]  # type: ignore
