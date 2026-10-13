"""Server-side configuration. Never return secrets to the browser."""
import os
from pathlib import Path
from dotenv import load_dotenv
import streamlit as st

load_dotenv(Path(__file__).parent / '.env')


def secret(name: str, default: str = '') -> str:
    try:
        value = st.secrets.get(name)
    except (FileNotFoundError, st.errors.StreamlitSecretNotFoundError):
        value = None
    return str(value) if value is not None else os.getenv(name, default)


# Change models here or override with PROVIDER_MODEL in secrets.
PROVIDERS = [
    {'name': 'Gemini', 'key': 'GEMINI_API_KEY', 'model': 'gemini-3.8-flash',
     'url': 'https://generativelanguage.googleapis.com/v1beta'},
    {'name': 'Groq', 'key': 'GROQ_API_KEY', 'model': 'openai/gpt-oss-120b',
     'url': 'https://api.groq.com/openai/v1/chat/completions'},
    {'name': 'OpenRouter', 'key': 'OPENROUTER_API_KEY', 'model': 'apodex/apodex-1.1-mini:free',
     'url': 'https://openrouter.ai/api/v1/chat/completions'},
    {'name': 'Mistral', 'key': 'MISTRAL_API_KEY', 'model': 'mistral-small-latest',
     'url': 'https://api.mistral.ai/v1/chat/completions'},
    {'name': 'Cerebras', 'key': 'CEREBRAS_API_KEY', 'model': 'gpt-oss-120b',
     'url': 'https://api.cerebras.ai/v1/chat/completions'},
]


def provider_accounts(provider: dict):
    for suffix in ('', '_2'):
        key = secret(provider['key'] + suffix)
        if key:
            yield (1 if not suffix else 2), key
