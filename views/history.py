import streamlit as st
import db
from ui import errors, preview, edit_application, downloads

st.title('Application History')
with errors():
    apps = db.applications()
    if not apps:
        st.info('No applications yet. Generate your first application from the sidebar.')
    else:
        selected = st.selectbox('Saved applications', apps,
            format_func=lambda app: f"{app['created_at'][:10]} · {app['company']} · {app['job_title']}")
        st.session_state['active_application'] = selected['id']
        with st.expander('Original job description'):
            st.write(selected['jd_text'])
        edit_application(selected, 'history_' + selected['id'])
        preview(selected)
        downloads(selected, 'history_' + selected['id'])
        if st.button('Prepare application email'):
            st.switch_page('views/send.py')
    st.subheader('Email history')
    st.dataframe(db.email_logs(), use_container_width=True, hide_index=True)
