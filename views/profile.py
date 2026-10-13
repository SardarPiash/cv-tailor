import streamlit as st
import db
import prompts
from schemas import Profile
from llm import generate_json, last_model
from importing import extract_text
from ui import errors
from editors import profile_editor, clear_editor

st.title('Master Profile')
st.caption('Your single source of truth. Only reviewed, saved facts are used in applications.')
with errors():
    profile = db.get_profile()
    fields = profile_editor(profile, 'master_')
    if st.button('Save master profile', type='primary'):
        with errors():
            db.save_profile(Profile.model_validate(fields).model_dump())
            clear_editor('master_')
            st.session_state['profile_notice'] = 'Profile saved.'
            st.rerun()
    if st.session_state.pop('profile_notice', None):
        st.success('Profile saved.')
    st.divider()
    st.subheader('Import an existing CV')
    upload = st.file_uploader('DOCX or text PDF', type=['docx', 'pdf'])
    if st.button('Extract and propose profile', disabled=upload is None):
        with errors(), st.spinner('Reading and structuring your CV…'):
            text = extract_text(upload.getvalue(), upload.name)
            proposal = generate_json(prompts.IMPORT, text, 'profile')
            st.session_state['import_proposal'] = proposal
            st.session_state['import_model'] = last_model()
            clear_editor('imported_')
    if 'import_proposal' in st.session_state:
        st.caption(st.session_state.get('import_model', ''))
        st.warning('Review every extracted field. Approve replaces the entire master profile; preserve any existing facts you want to keep.')
        imported = profile_editor(st.session_state['import_proposal'], 'imported_')
        if st.button('Approve imported profile'):
            with errors():
                db.save_profile(Profile.model_validate(imported).model_dump())
                del st.session_state['import_proposal']
                clear_editor('master_')
                clear_editor('imported_')
                st.session_state['profile_notice'] = 'Imported profile approved and saved.'
                st.rerun()
