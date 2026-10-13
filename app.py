import streamlit as st
from auth import require_login

st.set_page_config(page_title='CV Tailor', page_icon='📄', layout='wide')
# Register routes before the gate so direct links also enter through this script.
# Only this entrypoint owns login; pages share its authenticated session.
navigation = st.navigation([
    st.Page('views/profile.py', title='Master Profile', default=True),
    st.Page('views/daily.py', title='Daily Update'),
    st.Page('views/generate.py', title='Generate CV + Cover Letter'),
    st.Page('views/send.py', title='Send Email'),
    st.Page('views/history.py', title='History'),
    st.Page('views/settings.py', title='Settings'),
], position='sidebar' if st.session_state.get('authenticated') else 'hidden')
require_login()
with st.sidebar:
    st.title('CV Tailor')
    st.caption('Honest applications, built from your experience.')
    if st.button('Sign out'):
        st.session_state.clear()
        st.rerun()
navigation.run()
