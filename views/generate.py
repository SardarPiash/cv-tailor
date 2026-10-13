import streamlit as st
import db
from pipeline import generate_application
from ui import errors, preview, edit_application, downloads

st.title('Generate CV + Cover Letter')
st.caption('Paste a job description. AI selects and rephrases your saved facts; you review before export.')
with st.form('generate_application'):
    jd = st.text_area('Job description', height=230)
    a, b = st.columns(2)
    company = a.text_input('Company name')
    title = b.text_input('Job title')
    manager = a.text_input('Hiring manager (optional)')
    recruiter = b.text_input('Recruiter email (optional)')
    submitted = st.form_submit_button('Generate application', type='primary')
if submitted:
    with errors():
        if not jd.strip() or not company.strip() or not title.strip():
            raise ValueError('Job description, company and job title are required.')
        if len(jd) > 50000:
            raise ValueError('Job description is too long (maximum 50,000 characters).')
        profile = db.get_profile()
        if not profile['name'] or not (profile['experience'] or profile['projects'] or profile['education']):
            raise ValueError('Save a profile with your name and at least one experience, project or education entry first.')
        with st.status('Building your application…', expanded=True) as status:
            data, analysis, match = generate_application(profile, jd, company, title, manager, recruiter, lambda message: status.write(message))
            # Preserve expensive generated content if the final database save fails.
            st.session_state['unsaved_application'] = data
            saved = db.save_application(data)
            st.session_state.pop('unsaved_application', None)
            st.session_state['active_application'] = saved['id']
            st.session_state['analysis'] = analysis
            st.session_state['match'] = match
            status.update(label='Application generated and saved', state='complete')
if 'unsaved_application' in st.session_state:
    st.warning('Generated content is waiting to be saved. Retry without making new AI calls.')
    if st.button('Retry saving generated application'):
        with errors():
            saved = db.save_application(st.session_state['unsaved_application'])
            st.session_state['active_application'] = saved['id']
            st.session_state.pop('unsaved_application')
            st.rerun()
if st.session_state.get('analysis'):
    with st.expander('Job analysis and honest skill gaps'):
        st.json(st.session_state['analysis'])
        st.json(st.session_state.get('match', {}))
if st.session_state.get('active_application'):
    with errors():
        application = db.application(st.session_state['active_application'])
        edit_application(application, 'generated_' + application['id'])
        preview(application)
        downloads(application, 'generated_' + application['id'])
        if st.button('Prepare email for this application'):
            st.switch_page('views/send.py')
