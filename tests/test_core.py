import copy
import json
from io import BytesIO
from unittest.mock import Mock
import httpx
import pytest
from pydantic import ValidationError
from docx import Document
from pypdf import PdfReader
import llm
import emailer
from schemas import ProviderTest
from validator import validate_cv, validate_cover
from documents import page_count
import cv_template
import cover_letter_template
from importing import extract_text
from updates import apply_suggestion


def test_fenced_json_and_strict_contract():
    assert llm.parse_json('```json\n{"ok":true}\n```', ProviderTest) == {'ok': True}
    with pytest.raises(ValidationError):
        llm.parse_json('{"ok":true,"extra":1}', ProviderTest)


def test_account_fallback_order_and_model(monkeypatch):
    monkeypatch.setattr(llm, 'PROVIDERS', [{'name': 'First'}, {'name': 'Second'}])
    monkeypatch.setattr(llm, 'provider_accounts', lambda p: [(1, 'test-key'), (2, 'test-key-two')])
    calls = []
    def request(p, key, *args):
        calls.append((p['name'], key))
        if len(calls) < 3:
            raise ValueError('invalid json')
        return {'ok': True}, 'test-model'
    monkeypatch.setattr(llm, '_request', request)
    assert llm.generate_json('test', 'test', 'test') == {'ok': True}
    assert calls == [('First', 'test-key'), ('First', 'test-key-two'), ('Second', 'test-key')]
    assert llm.last_model() == 'Second / account 1 / test-model'


def test_all_failures_are_sanitized(monkeypatch):
    monkeypatch.setattr(llm, 'PROVIDERS', [{'name': 'First'}])
    monkeypatch.setattr(llm, 'provider_accounts', lambda p: [(1, 'secret-value')])
    monkeypatch.setattr(llm, '_request', Mock(side_effect=RuntimeError('secret-value is invalid')))
    with pytest.raises(llm.LLMError) as exc:
        llm.generate_json('test', 'test', 'test')
    assert 'secret-value' not in str(exc.value)


def test_fabricated_entities_and_dates_removed(profile, cv):
    cv['skills'][0]['items'].append('Kubernetes')
    cv['experience'][0]['start'] = '2020-01'
    cv['experience'][0]['bullets'] = ['Scaled service to 10000 users using Kubernetes.']
    cv['experience'].append({'company': 'Invented', 'title': 'CTO', 'location': '', 'start': '', 'end': '', 'bullets': []})
    cv['projects'][0]['tech'].append('Rust')
    cv['education'][0]['degree'] = 'PhD'
    result, warnings = validate_cv(cv, profile, {'required_skills': ['Kubernetes'], 'preferred_skills': []})
    assert result['skills'][0]['items'] == ['Python', 'SQL']
    assert len(result['experience']) == 1
    assert result['experience'][0]['start'] == '2024-01'
    assert result['education'] == []
    assert result['projects'][0]['tech'] == ['Python']
    assert any('10000' in warning for warning in warnings)
    assert any('Kubernetes' in warning for warning in warnings)
    assert profile['experience'][0]['start'] == '2024-01'


def test_numbers_must_belong_to_relevant_employer(profile, cv):
    profile['experience'].append({'company': 'Other Co', 'title': 'Engineer', 'location': '', 'start': '2020', 'end': '2022', 'bullets': ['Handled 50 requests.']})
    cv['experience'][0]['bullets'] = ['Handled 50 requests.']
    _, warnings = validate_cv(cv, profile)
    assert any('50' in w for w in warnings)


def test_unsupported_prose_always_flagged(profile, cv):
    cv['summary'] = 'Architected a distributed system using UnlistedTool.'
    cv['experience'][0]['bullets'] = ['Led the UnlistedCompany migration.']
    _, warnings = validate_cv(cv, profile)
    assert any('Summary: rephrased' in w for w in warnings)
    assert any('bullet 1: rephrased' in w for w in warnings)


def test_reverse_chronological(profile, cv):
    old = {'company': 'Old Co', 'title': 'Intern', 'location': '', 'start': '2020-01', 'end': '2021-01', 'bullets': []}
    profile['experience'].append(old)
    cv['experience'].insert(0, old)
    result, _ = validate_cv(cv, profile)
    assert result['experience'][0]['company'] == 'Real Co'


def test_cover_numbers_and_length(profile, cover):
    cover['body_experience'] = 'I managed 999 staff.'
    warnings = validate_cover(cover, profile)
    assert any('999' in w for w in warnings)
    assert any('250' in w for w in warnings)


def test_document_content_and_import(profile, cv, cover):
    docx = cv_template.docx(profile, cv)
    pdf = cv_template.pdf(profile, cv)
    text = extract_text(docx, 'CV.docx')
    assert 'Piash' in text and 'Work Experience' in text and 'Jan 2024 - Present' in text
    assert len(Document(BytesIO(docx)).tables) == 0
    pdf_text = '\n'.join(p.extract_text() for p in PdfReader(BytesIO(pdf)).pages)
    assert 'Piash' in pdf_text and 'Real Co' in pdf_text
    assert page_count(pdf) <= 2
    assert cover_letter_template.docx(profile, cover, 'Target Co')[:2] == b'PK'
    assert cover_letter_template.pdf(profile, cover, 'Target Co').startswith(b'%PDF')


def test_broken_upload():
    with pytest.raises(ValueError):
        extract_text(b'bad file', 'bad.pdf')


def test_update_requires_valid_target_and_no_mutation(profile):
    old = copy.deepcopy(profile)
    suggestion = {'kind': 'experience_bullet', 'target_index': 0, 'value': 'Fixed login validation.', 'log_ids': [1], 'evidence': 'fixed login'}
    result = apply_suggestion(profile, suggestion)
    assert result['experience'][0]['bullets'][-1] == suggestion['value']
    assert profile == old
    suggestion['target_index'] = -1
    with pytest.raises(ValueError):
        apply_suggestion(profile, suggestion)


def test_email_headers_recipients_and_attachments(monkeypatch):
    server = Mock()
    server.__enter__ = Mock(return_value=server)
    server.__exit__ = Mock(return_value=False)
    server.send_message.return_value = {}
    monkeypatch.setattr(emailer, '_connection', lambda: server)
    monkeypatch.setattr(emailer, 'secret', lambda k: 'sender@example.com')
    result = emailer.send('a@example.com', 'b@example.com', 'Application', 'Hello', [('CV.pdf', b'pdf', 'pdf')])
    assert result['status'] == 'sent'
    msg = server.send_message.call_args.args[0]
    assert server.send_message.call_args.kwargs['to_addrs'] == ['a@example.com', 'b@example.com']
    assert list(msg.iter_attachments())[0].get_filename() == 'CV.pdf'
    with pytest.raises(emailer.EmailError):
        emailer.send('invalid', '', 'Subject', 'Body')
    with pytest.raises(emailer.EmailError):
        emailer.send('a@example.com', '', 'Injected\nBCC: x@example.com', 'Body')


def test_email_partial_delivery(monkeypatch):
    server = Mock()
    server.__enter__ = Mock(return_value=server)
    server.__exit__ = Mock(return_value=False)
    server.send_message.return_value = {'b@example.com': (550, b'no')}
    monkeypatch.setattr(emailer, '_connection', lambda: server)
    monkeypatch.setattr(emailer, 'secret', lambda k: 'sender@example.com')
    assert emailer.send('a@example.com', 'b@example.com', 'Subject', 'Body')['status'] == 'partial'


def test_generated_cover_must_meet_word_range(cover):
    from schemas import CoverLetter
    # Short human drafts remain editable, but AI output must meet the brief.
    assert CoverLetter.model_validate(cover)
    with pytest.raises(ValidationError):
        llm.parse_json(json.dumps(cover), CoverLetter)
    cover['body_experience'] = ' '.join(['Experience'] * 260)
    assert llm.parse_json(json.dumps(cover), CoverLetter)['body_experience'] == cover['body_experience']


def test_missing_supabase_schema_has_actionable_error():
    from types import SimpleNamespace
    import db
    error = RuntimeError('sensitive provider detail')
    error.code = 'PGRST205'
    query = Mock()
    query.execute.side_effect = error
    with pytest.raises(db.DatabaseError) as exc:
        db.execute(query)
    assert 'Supabase connected' in str(exc.value)
    assert 'schema.sql' in str(exc.value)
    assert 'sensitive provider detail' not in str(exc.value)
