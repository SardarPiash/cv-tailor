"""Human-readable field editors with repeatable structured entries."""
import copy
from uuid import uuid4
import streamlit as st
from schemas import Skills, Experience, Project, Education, Certification

SECTIONS = {
    'skills': ('Skills', Skills, {'category': 'Category', 'items': 'Skills (one per line)'}),
    'experience': ('Work Experience', Experience, {'company': 'Company', 'title': 'Job title',
        'location': 'Location', 'start': 'Start date', 'end': 'End date', 'bullets': 'Achievement bullets (one per line)'}),
    'projects': ('Projects', Project, {'name': 'Project name', 'tech': 'Tech stack (one per line)',
        'description': 'Description', 'bullets': 'Achievement bullets (one per line)', 'link': 'Project link'}),
    'education': ('Education', Education, {'institution': 'Institution', 'degree': 'Degree',
        'start': 'Start date', 'end': 'End date', 'details': 'Details'}),
    'certifications': ('Certifications', Certification, {'name': 'Certification name', 'issuer': 'Issuer', 'year': 'Year'}),
}


def lines(value):
    return [line.strip() for line in value.splitlines() if line.strip()]


def record_editor(record, labels, prefix):
    result = copy.deepcopy(record)
    for field, label in labels.items():
        value = record.get(field, '')
        key = prefix + '_' + field
        if isinstance(value, list):
            result[field] = lines(st.text_area(label, '\n'.join(value), key=key, height=100))
        elif field in ('description', 'details', 'summary'):
            result[field] = st.text_area(label, value, key=key)
        else:
            result[field] = st.text_input(label, str(value), key=key)
    return result


def collection_editor(section, entries, prefix):
    title, model, labels = SECTIONS[section]
    state_key = prefix + '_rows_' + section
    if state_key not in st.session_state:
        st.session_state[state_key] = [{'uid': uuid4().hex, 'data': copy.deepcopy(entry)} for entry in entries]
    rows = st.session_state[state_key]
    result = []
    with st.expander(title, expanded=section == 'skills'):
        for i, row in enumerate(rows):
            st.markdown(f'**{title} entry {i + 1}**')
            row['data'] = record_editor(row['data'], labels, prefix + row['uid'])
            result.append(row['data'])
            if st.button('Remove entry', key=prefix + '_remove_' + row['uid']):
                rows.remove(row)
                st.rerun()
            st.divider()
        if st.button('Add ' + title.lower() + ' entry', key=prefix + '_add_' + section):
            defaults = {key: [] if key in ('items', 'bullets', 'tech') else '' for key in labels}
            rows.append({'uid': uuid4().hex, 'data': defaults})
            st.rerun()
    return result


def profile_editor(profile, prefix):
    result = copy.deepcopy(profile)
    a, b = st.columns(2)
    for i, (field, label) in enumerate([('name', 'Full name'), ('phone', 'Phone'), ('email', 'Email'),
        ('location', 'Location'), ('linkedin', 'LinkedIn'), ('portfolio', 'GitHub / portfolio')]):
        with (a if i % 2 == 0 else b):
            result[field] = st.text_input(label, profile.get(field, ''), key=prefix + field)
    result['summary'] = st.text_area('Professional summary', profile.get('summary', ''), key=prefix + 'summary')
    st.caption('Dates: YYYY-MM, a year, or Present. Keep achievement bullets factual.')
    for section in SECTIONS:
        result[section] = collection_editor(section, profile.get(section, []), prefix)
    result['languages'] = lines(st.text_area('Languages (one per line)', '\n'.join(profile.get('languages', [])), key=prefix + 'languages'))
    return result


def cv_editor(cv, prefix):
    result = copy.deepcopy(cv)
    result['summary'] = st.text_area('Professional summary', cv['summary'], key=prefix + 'summary')
    for section in SECTIONS:
        result[section] = collection_editor(section, cv[section], prefix)
    return result


def cover_editor(cover, prefix):
    labels = {'greeting': 'Greeting', 'opening': 'Opening paragraph', 'body_experience': 'Relevant experience',
              'body_skills': 'Skills and contribution', 'closing': 'Closing paragraph', 'sign_off': 'Sign-off'}
    return {field: st.text_area(label, cover[field], key=prefix + field,
            height=130 if field in ('opening', 'body_experience', 'body_skills', 'closing') else 70)
            for field, label in labels.items()}


def clear_editor(prefix):
    for key in list(st.session_state.keys()):
        if key.startswith(prefix):
            del st.session_state[key]
