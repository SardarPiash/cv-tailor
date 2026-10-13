import json
from datetime import date
import streamlit as st
import db
import prompts
from llm import generate_json, last_model
from schemas import Suggestion
from updates import apply_suggestion
from ui import errors
from editors import record_editor, clear_editor, SECTIONS

st.title('Daily Update')
st.caption('Write naturally in English or Bangla. Nothing enters your profile without your approval.')
with st.form('daily_entry', clear_on_submit=True):
    log_date = st.date_input('Work date', date.today())
    content = st.text_area('What did you do?', placeholder='Aj login form-er validation bug fix korechi…')
    if st.form_submit_button('Save daily log'):
        with errors():
            db.add_log(log_date, content)
            st.success('Daily log saved.')
with errors():
    logs = db.get_logs()
    unprocessed = [log for log in logs if not log['processed']]
    if st.button('Suggest profile updates', disabled=not unprocessed):
        with errors(), st.spinner('Finding factual profile updates…'):
            profile = db.get_profile()
            proposal = generate_json(prompts.UPDATES, json.dumps({'profile': profile, 'logs': unprocessed}, ensure_ascii=False), 'suggestions')
            ids = {log['id'] for log in unprocessed}
            if any(not item['log_ids'] or not set(item['log_ids']).issubset(ids) for item in proposal['suggestions']):
                raise ValueError('AI returned invalid source log IDs. Retry the suggestion request.')
            st.session_state['update_batch'] = {'suggestions': proposal['suggestions'],
                'log_ids': sorted(ids), 'decisions': {}, 'profile': profile, 'model': last_model()}
            clear_editor('suggestion_edit_')
    batch = st.session_state.get('update_batch')
    if batch:
        st.caption(batch['model'])
        if not batch['suggestions']:
            st.info('No profile updates proposed. You can finish review to mark these logs processed.')
        for i, item in enumerate(batch['suggestions']):
            with st.expander(f"Suggestion {i + 1}: {item['kind']} — {batch['decisions'].get(i, {}).get('decision', 'Pending')}", expanded=True):
                st.write('Evidence: ' + item['evidence'])
                for log in unprocessed:
                    if log['id'] in item['log_ids']:
                        st.caption(f"Log {log['id']} · {log['date']}: {log['content']}")
                edited = dict(item)
                prefix = f'suggestion_edit_{i}_'
                if item['kind'] == 'skill':
                    edited['category'] = st.text_input('Skill category', item['category'], key=prefix + 'category')
                    edited['value'] = st.text_input('Skill', item['value'], key=prefix + 'value')
                elif item['kind'] == 'experience_bullet':
                    experiences = batch['profile']['experience']
                    if experiences:
                        valid_index = item['target_index'] if item['target_index'] is not None and 0 <= item['target_index'] < len(experiences) else 0
                        edited['target_index'] = st.selectbox('Experience', list(range(len(experiences))), index=valid_index,
                            format_func=lambda n: f"{experiences[n]['title']} · {experiences[n]['company']}", key=prefix + 'target')
                    edited['value'] = st.text_area('Achievement bullet', item['value'], key=prefix + 'value')
                else:
                    defaults = {'name': '', 'tech': [], 'description': '', 'bullets': [], 'link': ''}
                    edited['project'] = record_editor(item['project'] or defaults, SECTIONS['projects'][2], prefix)
                a, b, c = st.columns(3)
                if a.button('Approve', key=f'approve_{i}'):
                    batch['decisions'][i] = {'decision': 'Approved', 'item': item}
                    st.rerun()
                if b.button('Edit and approve', key=f'edit_{i}'):
                    with errors():
                        edited = Suggestion.model_validate(edited).model_dump()
                        if not set(edited['log_ids']).issubset(set(batch['log_ids'])):
                            raise ValueError('Keep source IDs within the current batch.')
                        batch['decisions'][i] = {'decision': 'Approved', 'item': edited}
                        st.rerun()
                if c.button('Reject', key=f'reject_{i}'):
                    batch['decisions'][i] = {'decision': 'Rejected', 'item': item}
                    st.rerun()
        ready = len(batch['decisions']) == len(batch['suggestions'])
        if st.button('Save approved updates and mark logs processed', disabled=not ready):
            with errors():
                current = db.get_profile()
                if current != batch['profile']:
                    raise ValueError('Master profile changed during review. Generate a fresh suggestion batch to avoid overwriting your changes.')
                for decision in batch['decisions'].values():
                    if decision['decision'] == 'Approved':
                        current = apply_suggestion(current, decision['item'])
                db.approve_updates(current, batch['log_ids'])
                del st.session_state['update_batch']
                st.success('Approved updates saved. Reviewed logs marked processed.')
                st.rerun()
    st.subheader('Daily history')
    for log in logs:
        with st.expander(f"{log['date']} · {'Processed' if log['processed'] else 'Unprocessed'}"):
            st.write(log['content'])
