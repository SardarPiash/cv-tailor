import sys
from pathlib import Path
import pytest
from schemas import Profile, CV, CoverLetter

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


@pytest.fixture
def profile():
    return Profile(name='Piash', email='piash@example.com', phone='01700000000', location='Dhaka',
        summary='Python developer with 2 years of experience.',
        skills=[{'category': 'Programming', 'items': ['Python', 'SQL']}],
        experience=[{'company': 'Real Co', 'title': 'Developer', 'location': 'Dhaka',
            'start': '2024-01', 'end': 'Present', 'bullets': ['Fixed 2 login bugs using Python.']}],
        projects=[{'name': 'Tracker', 'tech': ['Python'], 'description': 'Daily work tracker',
            'bullets': ['Built a task tracker.'], 'link': 'https://example.com'}],
        education=[{'institution': 'University', 'degree': 'BSc', 'start': '2018', 'end': '2022', 'details': ''}],
        certifications=[{'name': 'SQL Certificate', 'issuer': 'Institute', 'year': '2023'}]).model_dump()


@pytest.fixture
def cv(profile):
    return CV(**{k: profile[k] for k in ('summary', 'skills', 'experience', 'projects', 'education', 'certifications')}).model_dump()


@pytest.fixture
def cover():
    return CoverLetter(greeting='Dear Hiring Manager,', opening='I am applying for Developer.',
        body_experience='I fixed login bugs using Python.', body_skills='I built a task tracker.',
        closing='Thank you for considering my application.', sign_off='Sincerely,').model_dump()


@pytest.fixture
def application(profile, cv, cover):
    return {'id': 'test-application', 'company': 'Target Co', 'job_title': 'Developer', 'jd_text': 'Python role',
        'cv_json': cv, 'cover_letter_json': cover, 'model_used': 'Mock model', 'profile_snapshot': profile,
        'recruiter_email': 'recruiter@example.com', 'email_json': {'subject': 'Application', 'body': 'Please see attachments.'},
        'warnings': [], 'reviewed': True, 'created_at': '2026-10-13T00:00:00+00:00'}
