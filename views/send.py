import hashlib
import streamlit as st
from config import secret
import db
from emailer import send, addresses, EmailError
from ui import errors, attachments
from documents import page_count

st.title('Send Email')
st.caption('Email sends only when you click Confirm & Send after reviewing the full preview.')
with errors():
    apps = db.applications()
    if not apps:
        st.info('Generate and review an application first.')
    else:
        index = next((i for i, a in enumerate(apps) if a['id'] == st.session_state.get('active_application')), 0)
        app = st.selectbox('Application', apps, index=index,
                           format_func=lambda a: f"{a['company']} · {a['job_title']} · {a['created_at'][:10]}")
        app_id = app['id']
        st.write('From: ' + secret('GMAIL_ADDRESS'))
        to = st.text_input('To', app.get('recruiter_email', ''), key='to_' + app_id)
        cc = st.text_input('CC (optional)', key='cc_' + app_id)
        draft = app.get('email_json', {})
        subject = st.text_input('Subject', draft.get('subject') or f"Application for {app['job_title']} - {app['profile_snapshot']['name']}", key='subject_' + app_id)
        body = st.text_area('Body', draft.get('body', ''), height=200, key='body_' + app_id)
        fmt = st.radio('Attachment format', ['PDF', 'DOCX'], horizontal=True)
        files = attachments(app, fmt)
        pdf_pages = page_count(attachments(app, 'PDF')[0][1])
        if pdf_pages > 2:
            st.warning('CV exceeds two pages. Shorten it in the application editor before sending.')
        if not app.get('reviewed'):
            st.warning('Approve your factual review in Generate or History before sending.')
        st.subheader('Full email preview')
        st.write({'From': secret('GMAIL_ADDRESS'), 'To': to, 'CC': cc, 'Subject': subject})
        st.text(body)
        for filename, content, subtype in files:
            st.download_button('Preview ' + filename, content, filename, mime='application/' + subtype, key='preview_' + filename)
        approved = st.checkbox('I reviewed the recipient, message and attachments and want to send this email.')
        fingerprint = hashlib.sha256((app_id + to + cc + subject + body + fmt + str(app['cv_json']) + str(app['cover_letter_json'])).encode()).hexdigest()
        if st.button('Confirm & Send', type='primary', disabled=not approved or not app.get('reviewed') or pdf_pages > 2):
            if st.session_state.get('sent_fingerprint') == fingerprint:
                st.warning('This exact message was already accepted by Gmail in this session. Edit the message to prepare a new send.')
            else:
                with errors():
                    addresses(to)
                    addresses(cc, optional=True)
                    if not body.strip():
                        raise ValueError('Enter an email body.')
                    # Record the attempt BEFORE sending. If logging is unavailable, do not send.
                    record = db.log_email({'application_id': app_id, 'to_email': to,
                        'subject': subject, 'status': 'pending', 'error': None})[0]
                    try:
                        with st.spinner('Sending through Gmail…'):
                            result = send(to, cc, subject, body, files)
                        st.session_state['sent_fingerprint'] = fingerprint
                    except EmailError as exc:
                        db.execute(db.client().table('email_logs').update({'status': 'failed', 'error': str(exc)}).eq('id', record['id']))
                        st.error(str(exc))
                    else:
                        try:
                            db.execute(db.client().table('email_logs').update(result).eq('id', record['id']))
                        except db.DatabaseError:
                            st.warning('Gmail accepted the message, but updating the email log failed. Do not retry sending; the pending log records this attempt.')
                        if result['status'] == 'partial':
                            st.warning(result['error'])
                        else:
                            st.success('Gmail accepted the email for delivery.')
