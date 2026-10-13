"""Separate, observable JD analysis, matching, content and validation stages."""
import json
from llm import generate_json, last_model
import prompts
from validator import validate_cv, validate_cover


def generate_application(profile, jd_text, company, job_title, manager='', recruiter='', progress=None):
    models = []
    def call(label, system, data, schema):
        if progress:
            progress(label)
        result = generate_json(system, json.dumps(data, ensure_ascii=False), schema)
        models.append(label + ': ' + last_model())
        return result
    jd = call('A · Analyze job description', prompts.JD, {'jd_text': jd_text, 'company': company, 'job_title': job_title}, 'jd')
    match = call('B · Match real experience', prompts.MATCH, {'profile': profile, 'jd': jd}, 'match')
    # Indices are advisory; do not let an invalid index select unrelated data.
    if any(i < 0 or i >= len(profile['experience']) for i in match['experience_indices']):
        raise ValueError('AI matching returned an invalid experience index. Please retry.')
    if any(i < 0 or i >= len(profile['projects']) for i in match['project_indices']):
        raise ValueError('AI matching returned an invalid project index. Please retry.')
    data = {'profile': profile, 'jd': jd, 'match': match, 'company': company,
            'job_title': job_title, 'hiring_manager': manager}
    raw_cv = call('C · Tailor CV', prompts.CV, data, 'cv')
    if progress:
        progress('D · Validate against master profile')
    cv, warnings = validate_cv(raw_cv, profile, jd)
    cover = call('E · Write cover letter', prompts.COVER, data, 'cover_letter')
    warnings += validate_cover(cover, profile, company, job_title, jd)
    email = call('Prepare editable email', prompts.EMAIL, data, 'email')
    return {'company': company, 'job_title': job_title, 'jd_text': jd_text, 'cv_json': cv,
            'cover_letter_json': cover, 'model_used': '\n'.join(models),
            'profile_snapshot': profile, 'recruiter_email': recruiter, 'hiring_manager': manager,
            'email_json': email, 'warnings': warnings, 'reviewed': False}, jd, match
