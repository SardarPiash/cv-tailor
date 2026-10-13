from pathlib import Path
from unittest.mock import Mock
import pytest
from streamlit.testing.v1 import AppTest
import auth
import db

ROOT = Path(__file__).resolve().parents[1]


def test_login_blocks_navigation(monkeypatch):
    monkeypatch.setattr(auth, 'secret', lambda key: 'test-password')
    test = AppTest.from_file(str(ROOT / 'app.py')).run()
    assert not test.exception
    assert test.title[0].value == 'CV Tailor'
    assert len(test.text_input) == 1
    test.text_input[0].set_value('wrong')
    test.button[0].click().run()
    assert test.error[0].value == 'Incorrect password.'
    assert 'authenticated' not in test.session_state


@pytest.mark.parametrize('page', ['profile', 'daily', 'generate', 'send', 'history', 'settings'])
def test_every_page_requires_login(page, monkeypatch):
    monkeypatch.setattr(auth, 'secret', lambda key: 'test-password')
    test = AppTest.from_file(str(ROOT / 'app.py')).run()
    test.switch_page(f'views/{page}.py').run()
    assert not test.exception
    assert test.title[0].value == 'CV Tailor'
    assert not test.dataframe


def test_single_login_covers_navigation_and_logout(monkeypatch, profile, application):
    monkeypatch.setattr(auth, 'secret', lambda key: 'test-password')
    monkeypatch.setattr(db, 'get_profile', lambda: profile)
    monkeypatch.setattr(db, 'get_logs', lambda *args, **kwargs: [])
    monkeypatch.setattr(db, 'applications', lambda: [application])
    monkeypatch.setattr(db, 'application', lambda _: application)
    monkeypatch.setattr(db, 'email_logs', lambda: [])
    test = AppTest.from_file(str(ROOT / 'app.py')).run()
    test.text_input[0].set_value('test-password')
    next(b for b in test.button if b.label == 'Sign in').click().run()
    for page in ('profile', 'daily', 'generate', 'send', 'history', 'settings', 'profile'):
        test.switch_page(f'views/{page}.py').run()
        assert not test.exception
        assert test.session_state['authenticated']
        assert not any(field.label == 'App password' for field in test.text_input)
    next(b for b in test.button if b.label == 'Sign out').click().run()
    assert not test.exception
    assert any(field.label == 'App password' for field in test.text_input)
    test.switch_page('views/history.py').run()
    assert any(field.label == 'App password' for field in test.text_input)
    assert not test.dataframe


@pytest.mark.parametrize('page', ['profile', 'daily', 'generate', 'send', 'history', 'settings'])
def test_pages_render_authenticated(page, monkeypatch, profile, application):
    monkeypatch.setattr(auth, 'secret', lambda key: 'test-password')
    monkeypatch.setattr(db, 'get_profile', lambda: profile)
    monkeypatch.setattr(db, 'get_logs', lambda *args, **kwargs: [])
    monkeypatch.setattr(db, 'applications', lambda: [application])
    monkeypatch.setattr(db, 'application', lambda _: application)
    monkeypatch.setattr(db, 'email_logs', lambda: [])
    test = AppTest.from_file(str(ROOT / 'views' / f'{page}.py'))
    test.session_state['authenticated'] = True
    test.run()
    assert not test.exception


def test_email_does_not_send_without_click(monkeypatch, application):
    import emailer
    sender = Mock()
    monkeypatch.setattr(emailer, 'send', sender)
    monkeypatch.setattr(db, 'applications', lambda: [application])
    test = AppTest.from_file(str(ROOT / 'views' / 'send.py'))
    test.session_state['authenticated'] = True
    test.run()
    assert not test.exception
    sender.assert_not_called()
    buttons = [b for b in test.button if b.label == 'Confirm & Send']
    assert buttons[0].disabled


def test_profile_field_save_and_add_entry(monkeypatch, profile):
    saved = []
    monkeypatch.setattr(db, 'get_profile', lambda: saved[-1] if saved else profile)
    monkeypatch.setattr(db, 'save_profile', lambda p: saved.append(p))
    test = AppTest.from_file(str(ROOT / 'views' / 'profile.py'))
    test.session_state['authenticated'] = True
    test.run()
    next(b for b in test.button if b.label == 'Add work experience entry').click().run()
    assert not test.exception
    companies = [x for x in test.text_input if x.label == 'Company']
    companies[-1].set_value('Second Co')
    titles = [x for x in test.text_input if x.label == 'Job title']
    titles[-1].set_value('Engineer')
    next(b for b in test.button if b.label == 'Save master profile').click().run()
    assert not test.exception
    assert saved[-1]['experience'][-1]['company'] == 'Second Co'
    assert saved[-1]['experience'][-1]['title'] == 'Engineer'


def test_review_save_sanitizes_application(monkeypatch, application):
    monkeypatch.setattr(db, 'applications', lambda: [application])
    monkeypatch.setattr(db, 'email_logs', lambda: [])
    saved = []
    def update(app_id, values):
        saved.append(values)
        application.update(values)
        return application
    monkeypatch.setattr(db, 'update_application', update)
    test = AppTest.from_file(str(ROOT / 'views' / 'history.py'))
    test.session_state['authenticated'] = True
    test.run()
    skill = next(x for x in test.text_area if x.label == 'Skills (one per line)')
    skill.set_value('Python\nSQL\nInventedSkill')
    next(b for b in test.button if b.label == 'Validate and save edits').click().run()
    assert not test.exception
    assert saved[-1]['cv_json']['skills'][0]['items'] == ['Python', 'SQL']
    assert any('InventedSkill' in warning for warning in saved[-1]['warnings'])


def test_email_confirmation_and_log_before_send(monkeypatch, application):
    import emailer
    order = []
    monkeypatch.setattr(db, 'applications', lambda: [application])
    monkeypatch.setattr(db, 'log_email', lambda values: order.append('log') or [{'id': 42}])
    def sender(*args):
        order.append('send')
        return {'status': 'sent', 'error': None}
    monkeypatch.setattr(emailer, 'send', sender)
    query = Mock()
    monkeypatch.setattr(db, 'client', lambda: query)
    monkeypatch.setattr(db, 'execute', lambda q: order.append('update') or [])
    test = AppTest.from_file(str(ROOT / 'views' / 'send.py'))
    test.session_state['authenticated'] = True
    test.run()
    test.checkbox[0].check().run()
    next(b for b in test.button if b.label == 'Confirm & Send').click().run()
    assert not test.exception
    assert order == ['log', 'send', 'update']
    next(b for b in test.button if b.label == 'Confirm & Send').click().run()
    assert order == ['log', 'send', 'update']
    assert any('already accepted' in w.value for w in test.warning)


def test_daily_approval_writes_only_after_finish(monkeypatch, profile):
    import llm
    log = {'id': 1, 'date': '2026-10-13', 'content': 'Fixed login validation.', 'processed': False}
    suggestion = {'kind': 'experience_bullet', 'target_index': 0, 'category': '', 'value': 'Fixed login validation.',
                  'project': None, 'log_ids': [1], 'evidence': log['content']}
    monkeypatch.setattr(db, 'get_logs', lambda *args: [log])
    monkeypatch.setattr(db, 'get_profile', lambda: profile)
    monkeypatch.setattr(llm, 'generate_json', lambda *args: {'suggestions': [suggestion]})
    approvals = []
    monkeypatch.setattr(db, 'approve_updates', lambda p, ids: approvals.append((p, ids)))
    test = AppTest.from_file(str(ROOT / 'views' / 'daily.py'))
    test.session_state['authenticated'] = True
    test.run()
    next(b for b in test.button if b.label == 'Suggest profile updates').click().run()
    assert not test.exception
    assert not approvals
    next(b for b in test.button if b.label == 'Approve').click().run()
    assert not approvals
    next(b for b in test.button if b.label == 'Save approved updates and mark logs processed').click().run()
    assert not test.exception
    assert approvals[0][1] == [1]
    assert approvals[0][0]['experience'][0]['bullets'][-1] == 'Fixed login validation.'
