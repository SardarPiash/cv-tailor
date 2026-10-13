"""Shared editors, preview and database error boundary."""
from contextlib import contextmanager
import streamlit as st
from pydantic import ValidationError
from db import DatabaseError
from llm import LLMError
from schemas import CV, CoverLetter
from validator import validate_cv, validate_cover
import cv_template
import cover_letter_template
from documents import page_count, cv_blocks, cover_blocks
from editors import cv_editor, cover_editor, clear_editor


@contextmanager
def errors():
    try:
        yield
    except (DatabaseError, LLMError, ValueError) as exc:
        if isinstance(exc, ValidationError):
            st.error('Data format is invalid. Check the required fields and JSON structure.')
        else:
            st.error(str(exc))
    except Exception:
        st.error('This operation could not be completed. Check your configuration and try again.')


def preview(application):
    st.subheader(f"{application['job_title']} · {application['company']}")
    st.caption(application['model_used'])
    profile = application['profile_snapshot']
    cv, cover = application['cv_json'], application['cover_letter_json']
    left, right = st.columns(2)
    with left:
        st.markdown('**CV**')
        for kind, text in cv_blocks(profile, cv):
            if kind in ('name', 'heading', 'title'):
                st.markdown(f'**{text}**')
            elif kind == 'bullet':
                st.write('• ' + text)
            else:
                st.write(text)
    with right:
        st.markdown('**Cover letter**')
        for _, text in cover_blocks(profile, cover, application['company'], application['created_at'][:10]):
            st.write(text)


def edit_application(application, prefix):
    import db
    app_id = application['id']
    with st.expander('Edit CV and cover letter', expanded=False):
        st.caption('Edit any content field. Add or remove entries as needed. Contact details come from the saved profile snapshot.')
        cv = cv_editor(application['cv_json'], prefix + '_cv_')
        cover = cover_editor(application['cover_letter_json'], prefix + '_cover_')
        reviewed = st.checkbox('I checked all claims against my real experience, including paraphrased text.',
                              value=application.get('reviewed', False), key=prefix + '_reviewed')
        if st.button('Validate and save edits', key=prefix + '_save'):
            with errors():
                cv = CV.model_validate(cv).model_dump()
                cover = CoverLetter.model_validate(cover).model_dump()
                cv, warnings = validate_cv(cv, application['profile_snapshot'])
                warnings += validate_cover(cover, application['profile_snapshot'], application['company'], application['job_title'])
                db.update_application(app_id, {'cv_json': cv, 'cover_letter_json': cover,
                    'warnings': warnings, 'reviewed': reviewed})
                clear_editor(prefix + '_cv_')
                clear_editor(prefix + '_cover_')
                st.rerun()
    for warning in application.get('warnings', []):
        st.warning(warning)
    if not application.get('reviewed'):
        st.info('Review the factual claims and save your approval in the editor before export or email. Automated checks cannot prove every paraphrase.')


def attachments(application, fmt='PDF'):
    p = application['profile_snapshot']
    args = (p, application['cover_letter_json'], application['company'], application['created_at'][:10])
    if fmt == 'PDF':
        return [('CV.pdf', cv_template.pdf(p, application['cv_json']), 'pdf'),
                ('Cover_Letter.pdf', cover_letter_template.pdf(*args), 'pdf')]
    subtype = 'vnd.openxmlformats-officedocument.wordprocessingml.document'
    return [('CV.docx', cv_template.docx(p, application['cv_json']), subtype),
            ('Cover_Letter.docx', cover_letter_template.docx(*args), subtype)]


def downloads(application, prefix):
    if not application.get('reviewed'):
        return
    with errors():
        pdf_files = attachments(application)
        pages = page_count(pdf_files[0][1])
        st.caption(f'CV PDF: {pages} page(s). DOCX and PDF share the same content and style; pagination can differ by viewer/font.')
        if pages > 2:
            st.warning('CV exceeds the two-page maximum. Shorten the summary/bullets or remove less relevant entries before export.')
            return
        cols = st.columns(4)
        for i, (filename, content, subtype) in enumerate(pdf_files + attachments(application, 'DOCX')):
            cols[i].download_button(filename, content, file_name=filename, mime='application/' + subtype, key=prefix + filename)
