import hmac
import time
import streamlit as st
from config import secret


def require_login():
    password = secret('APP_PASSWORD')
    if not password:
        st.error('Set APP_PASSWORD in .env or Cloud Secrets, then restart the app.')
        st.stop()
    if st.session_state.get('authenticated'):
        return
    st.title('CV Tailor')
    st.caption('Your real experience. A focused application.')
    with st.form('login'):
        entered = st.text_input('App password', type='password')
        submitted = st.form_submit_button('Sign in')
    if submitted:
        if time.time() < st.session_state.get('login_retry_at', 0):
            st.error('Please wait a few seconds before trying again.')
        elif hmac.compare_digest(entered.encode(), password.encode()):
            st.session_state['authenticated'] = True
            st.rerun()
        else:
            st.session_state['login_retry_at'] = time.time() + 3
            st.error('Incorrect password.')
    st.stop()
