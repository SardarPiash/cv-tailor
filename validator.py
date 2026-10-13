"""Deterministic checks supplement (not replace) human review of paraphrases."""
import copy
import json
import re
from datetime import datetime

BANNED = ['passionate', 'rockstar', 'ninja', 'guru', 'go-getter', 'synergy',
          'world-class', 'results-driven', 'think outside the box']


def normalize(text):
    return re.sub(r'\s+', ' ', str(text).casefold()).strip()


def numbers(text):
    return set(re.findall(r'(?<!\w)\d+(?:[.,]\d+)*(?:\s*%)?', text))


def contains(text, term):
    return bool(re.search(r'(?<!\w)' + re.escape(normalize(term)) + r'(?!\w)', normalize(text)))


def _text_checks(text, source, path, warnings):
    unsupported = numbers(text) - numbers(source)
    if unsupported:
        warnings.append(f"{path}: numbers not supported by the relevant source: {', '.join(sorted(unsupported))}")
    for word in BANNED:
        if contains(text, word):
            warnings.append(f'{path}: remove cliché "{word}".')


def _prose_review(text, source, path, warnings):
    if text.strip() and normalize(text) not in normalize(source):
        warnings.append(f'{path}: rephrased or new text — review all factual claims, names, tools and numbers against the source.')


def _source_date(value):
    if not value:
        return datetime.min
    if normalize(value) in ('present', 'current', 'now'):
        return datetime.max
    for fmt in ('%Y-%m', '%Y-%m-%d', '%b %Y', '%B %Y', '%Y'):
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            pass
    return datetime.min


def validate_cv(cv, profile, jd=None):
    result = copy.deepcopy(cv)
    warnings = []
    source = json.dumps(profile, ensure_ascii=False)
    allowed_skills = {normalize(item) for group in profile['skills'] for item in group['items']}
    allowed_tools = allowed_skills | {normalize(t) for p in profile['projects'] for t in p['tech']}
    for group in result['skills']:
        retained = []
        for skill in group['items']:
            if normalize(skill) in allowed_skills:
                retained.append(skill)
            else:
                warnings.append(f'Removed unsupported skill: {skill}')
        group['items'] = retained
    result['skills'] = [s for s in result['skills'] if s['items']]
    identity = {'experience': ('company', 'title'), 'projects': ('name',),
                'education': ('institution', 'degree'), 'certifications': ('name', 'issuer')}
    immutable = {'experience': ('company', 'title', 'location', 'start', 'end'),
                 'projects': ('name', 'link'),
                 'education': ('institution', 'degree', 'start', 'end'),
                 'certifications': ('name', 'issuer', 'year')}
    for section, keys in identity.items():
        kept = []
        for entry in result[section]:
            original = next((item for item in profile[section]
                if all(normalize(entry.get(k, '')) == normalize(item.get(k, '')) for k in keys)), None)
            if original is None:
                warnings.append(f'Removed unsupported {section} entry: {entry.get(keys[0], "")}')
                continue
            for field in immutable[section]:
                if entry.get(field, '') != original.get(field, ''):
                    warnings.append(f'{section}.{field}: restored master profile value.')
                    entry[field] = original.get(field, '')
            if section == 'projects':
                real_tech = {normalize(t) for t in original['tech']}
                for tool in entry['tech']:
                    if normalize(tool) not in real_tech:
                        warnings.append(f'Removed unsupported project tool: {tool}')
                entry['tech'] = [t for t in entry['tech'] if normalize(t) in real_tech]
            _text_checks(json.dumps(entry, ensure_ascii=False), json.dumps(original, ensure_ascii=False), section, warnings)
            original_text = json.dumps(original, ensure_ascii=False)
            for index, bullet in enumerate(entry.get('bullets', [])):
                _prose_review(bullet, original_text, f'{section} / {entry.get(keys[0], "")} / bullet {index + 1}', warnings)
            for field in ('description', 'details'):
                if field in entry:
                    _prose_review(entry[field], original_text, f'{section}.{field}', warnings)
            kept.append(entry)
        result[section] = kept
    result['experience'].sort(key=lambda e: _source_date(e['start']), reverse=True)
    _text_checks(result['summary'], source, 'Summary', warnings)
    _prose_review(result['summary'], source, 'Summary', warnings)
    # Flag JD technologies that leaked into free-text summaries or bullets.
    prose = result['summary'] + ' ' + ' '.join(
        ' '.join(e.get('bullets', [])) for section in ('experience', 'projects') for e in result[section])
    if jd:
        for term in jd.get('required_skills', []) + jd.get('preferred_skills', []):
            if normalize(term) not in allowed_tools and contains(prose, term) and not contains(source, term):
                warnings.append(f'Unsupported JD requirement mentioned in CV prose: {term}')
    # Proper names/tools inside free text cannot be exhaustively identified in Python.
    # Require visible human review for every application, even with no warnings.
    return result, list(dict.fromkeys(warnings))


def validate_cover(letter, profile, company='', job_title='', jd=None):
    warnings = []
    text = ' '.join(letter.values())
    source = json.dumps(profile, ensure_ascii=False) + ' ' + company + ' ' + job_title
    _text_checks(text, source, 'Cover letter', warnings)
    for field in ('opening', 'body_experience', 'body_skills', 'closing'):
        _prose_review(letter[field], source, f'Cover letter.{field}', warnings)
    if jd:
        for term in jd.get('required_skills', []) + jd.get('preferred_skills', []):
            if contains(text, term) and not contains(source, term):
                warnings.append(f'Cover letter: verify unsupported requirement mention: {term}')
    count = len(text.split())
    if not 250 <= count <= 350:
        warnings.append(f'Cover letter has {count} words; target is 250–350.')
    return warnings
