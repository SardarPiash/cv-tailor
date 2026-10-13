import streamlit as st
from pathlib import Path
from urllib.parse import urlparse
from config import PROVIDERS, provider_accounts, secret
from llm import test_providers
from emailer import test_connection, send, EmailError
from ui import errors
import db

st.title('Settings')
st.caption('Only configuration status is shown. Keys and passwords remain on the server.')
st.subheader('AI providers')
rows = []
for provider in PROVIDERS:
    configured = {account for account, _ in provider_accounts(provider)}
    rows.append({'Provider': provider['name'], 'Account 1': 'Configured' if 1 in configured else 'Missing',
                 'Account 2': 'Configured' if 2 in configured else 'Missing',
                 'Model': secret(provider['key'].replace('_API_KEY', '_MODEL'), provider['model'])})
st.dataframe(rows, hide_index=True, use_container_width=True)
st.caption('Fallback: Gemini account 1 → 2 → Groq account 1 → 2 → OpenRouter account 1 → 2 → Mistral → Cerebras. Missing keys are skipped. Rate limits may be shared between accounts/projects.')
if st.button('Test AI providers'):
    with st.spinner('Testing each configured account…'):
        st.dataframe(test_providers(), hide_index=True)
st.subheader('Supabase')
st.write('URL: ' + ('Configured' if secret('SUPABASE_URL') else 'Missing'))
st.write('Server-side key: ' + ('Configured' if secret('SUPABASE_KEY') else 'Missing'))
if st.button('Test database connection'):
    with errors():
        db.get_profile()
        st.success('Supabase connection works.')
with st.expander('Database setup'):
    st.write('Open the Supabase project SQL Editor, create a new query, paste the SQL below and click Run. Then test the database connection above.')
    host = urlparse(secret('SUPABASE_URL')).hostname or ''
    sql_editor = ('https://supabase.com/dashboard/project/' + host.split('.')[0] + '/sql/new'
                  if host.endswith('.supabase.co') else 'https://supabase.com/dashboard')
    st.link_button('Open Supabase SQL Editor', sql_editor)
    st.code((Path(__file__).resolve().parents[1] / 'schema.sql').read_text(), language='sql')
st.subheader('Gmail')
st.write('Sender: ' + (secret('GMAIL_ADDRESS') or 'Missing'))
st.write('App Password: ' + ('Configured' if secret('GMAIL_APP_PASSWORD') else 'Missing'))
if st.button('Test Gmail connection'):
    try:
        with st.spinner('Connecting to Gmail…'):
            test_connection()
        st.success('Gmail authentication works. No email was sent.')
    except EmailError as exc:
        st.error(str(exc))
if st.button('Send test email to myself'):
    with errors():
        record = db.log_email({'application_id': None, 'to_email': secret('GMAIL_ADDRESS'),
                              'subject': 'CV Tailor connection test', 'status': 'pending', 'error': None})[0]
        try:
            result = send(secret('GMAIL_ADDRESS'), '', 'CV Tailor connection test', 'Your CV Tailor Gmail connection is working.')
        except EmailError as exc:
            db.execute(db.client().table('email_logs').update({'status': 'failed', 'error': str(exc)}).eq('id', record['id']))
            st.error(str(exc))
        else:
            try:
                db.execute(db.client().table('email_logs').update(result).eq('id', record['id']))
            except db.DatabaseError:
                st.warning('Test email accepted by Gmail; email log update failed. Do not resend just to repair the log.')
            st.success('Test email accepted by Gmail. Check your inbox.')
st.subheader('Where to put secrets')
st.write('Locally: edit .env in the project folder. On Streamlit Community Cloud: App Settings → Secrets; copy the format from .streamlit/secrets.toml.example. Restart after changing secrets.')
