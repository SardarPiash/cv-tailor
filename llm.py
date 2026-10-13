"""Provider/account fallback with validated JSON and sanitized errors."""
import contextvars
import json
import re
import httpx
from pydantic import ValidationError
from config import PROVIDERS, provider_accounts, secret
from schemas import SCHEMAS

_last_model = contextvars.ContextVar('last_model', default='')


class LLMError(RuntimeError):
    pass


def last_model() -> str:
    return _last_model.get()


def parse_json(raw: str, model):
    # One parsing retry after removing a Markdown fence. No silent coercion.
    try:
        return model.model_validate(json.loads(raw), context={'generation': True}).model_dump()
    except json.JSONDecodeError:
        cleaned = re.sub(r'^\s*```(?:json)?\s*|\s*```\s*$', '', raw.strip(), flags=re.I)
        return model.model_validate(json.loads(cleaned), context={'generation': True}).model_dump()


def _request(provider, key, system, user, schema_name):
    model = secret(provider['key'].replace('_API_KEY', '_MODEL'), provider['model'])
    if provider['name'] == 'OpenRouter' and not model.endswith(':free'):
        raise LLMError('OpenRouter model must end in :free.')
    schema = SCHEMAS[schema_name].model_json_schema()
    system += '\nJSON schema:\n' + json.dumps(schema)
    with httpx.Client(timeout=httpx.Timeout(60, connect=10)) as client:
        if provider['name'] == 'Gemini':
            response = client.post(
                f"{provider['url']}/models/{model}:generateContent",
                headers={'x-goog-api-key': key},
                json={'systemInstruction': {'parts': [{'text': system}]},
                      'contents': [{'role': 'user', 'parts': [{'text': user}]}],
                      'generationConfig': {'temperature': 0.25, 'responseMimeType': 'application/json',
                                           'maxOutputTokens': 12000}})
            response.raise_for_status()
            data = response.json()
            raw = ''.join(part.get('text', '') for part in data['candidates'][0]['content']['parts']
                          if not part.get('thought'))
            actual_model = data.get('modelVersion', model)
        else:
            response = client.post(provider['url'], headers={'Authorization': f'Bearer {key}'},
                json={'model': model, 'messages': [{'role': 'system', 'content': system},
                      {'role': 'user', 'content': user}], 'temperature': 0.25,
                      'max_tokens': 8000, 'response_format': {'type': 'json_object'}})
            response.raise_for_status()
            data = response.json()
            raw = data['choices'][0]['message']['content']
            actual_model = data.get('model', model)
    return parse_json(raw, SCHEMAS[schema_name]), actual_model


def generate_json(system_prompt: str, user_prompt: str, schema_name: str) -> dict:
    if schema_name not in SCHEMAS:
        raise LLMError('Unknown response schema.')
    _last_model.set('')
    failures = []
    for provider in PROVIDERS:
        for account, key in provider_accounts(provider):
            try:
                result, model = _request(provider, key, system_prompt, user_prompt, schema_name)
                _last_model.set(f"{provider['name']} / account {account} / {model}")
                return result
            except Exception as exc:
                # Never show raw provider errors: they can contain a key, URL or prompt.
                if isinstance(exc, httpx.HTTPStatusError):
                    reason = f'HTTP {exc.response.status_code}'
                elif isinstance(exc, httpx.TimeoutException):
                    reason = 'timeout'
                elif isinstance(exc, (ValidationError, ValueError, KeyError, IndexError, TypeError)):
                    reason = 'invalid response or JSON'
                else:
                    reason = 'connection or provider failure'
                failures.append(f"{provider['name']} account {account}: {reason}")
    if not failures:
        raise LLMError('No AI keys configured. Add at least one provider key in Settings/secrets.')
    raise LLMError('All configured AI accounts failed. ' + '; '.join(failures))


def test_providers():
    results = []
    for provider in PROVIDERS:
        for account, key in provider_accounts(provider):
            try:
                _, model = _request(provider, key, 'Return JSON with ok=true.', 'Connection test.', 'test')
                results.append({'provider': provider['name'], 'account': account, 'status': 'OK', 'model': model})
            except Exception:
                results.append({'provider': provider['name'], 'account': account, 'status': 'Failed (check key/model/quota)', 'model': provider['model']})
    return results
