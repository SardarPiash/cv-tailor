"""Supabase service functions; client stays on the server, behind the gate."""
from datetime import datetime, timezone
from functools import lru_cache
from supabase import create_client
from config import secret
from schemas import Profile


class DatabaseError(RuntimeError):
    pass


@lru_cache(maxsize=1)
def client():
    url, key = secret('SUPABASE_URL'), secret('SUPABASE_KEY')
    if not url or not key:
        raise DatabaseError('Supabase is not configured. Add SUPABASE_URL and SUPABASE_KEY to .env or Cloud Secrets, then run schema.sql.')
    try:
        return create_client(url, key)
    except Exception:
        raise DatabaseError('Supabase configuration is invalid. Check URL and server-side key.') from None


def execute(query):
    try:
        return query.execute().data
    except Exception as exc:
        if getattr(exc, 'code', None) in ('PGRST205', 'PGRST202', '42P01', '42883'):
            raise DatabaseError('Supabase connected, but database tables or functions are missing. Run schema.sql in the Supabase SQL Editor. You can copy the SQL from Settings → Database setup.') from None
        raise DatabaseError('Database request failed. Check Supabase URL/key, connectivity, and that schema.sql has been run.') from None


def get_profile():
    rows = execute(client().table('profile').select('data').eq('id', 1))
    return Profile.model_validate(rows[0]['data']).model_dump() if rows else Profile().model_dump()


def save_profile(profile):
    data = Profile.model_validate(profile).model_dump()
    execute(client().table('profile').upsert({'id': 1, 'data': data,
        'updated_at': datetime.now(timezone.utc).isoformat()}))


def add_log(date, content):
    if not content.strip():
        raise ValueError('Please enter your daily work first.')
    return execute(client().table('daily_logs').insert({'date': str(date), 'content': content.strip()}))[0]


def get_logs(unprocessed=False):
    query = client().table('daily_logs').select('*').order('date', desc=True)
    if unprocessed:
        query = query.eq('processed', False)
    return execute(query)


def approve_updates(profile, log_ids):
    # Profile write and log processing are atomic, avoiding half-applied batches.
    return execute(client().rpc('approve_profile_updates', {
        'new_profile': Profile.model_validate(profile).model_dump(), 'log_ids': log_ids}))


def save_application(data):
    return execute(client().table('applications').insert(data))[0]


def update_application(application_id, data):
    return execute(client().table('applications').update(data).eq('id', application_id))[0]


def applications():
    return execute(client().table('applications').select('*').order('created_at', desc=True).limit(100))


def application(application_id):
    rows = execute(client().table('applications').select('*').eq('id', application_id))
    if not rows:
        raise DatabaseError('Application no longer exists.')
    return rows[0]


def log_email(data):
    return execute(client().table('email_logs').insert(data))


def email_logs():
    return execute(client().table('email_logs').select('*').order('sent_at', desc=True).limit(100))
