"""
Supabase clients for backend use.

Two flavours:
  - admin_client()            — service_role key, bypasses RLS.
                                Use only inside trusted server paths (caches,
                                background jobs, schema-level operations).
  - user_client(access_token) — anon key + caller's JWT, so RLS is enforced
                                as that user. Use from request handlers.
"""

from functools import lru_cache

from supabase import Client, create_client

from app.core.config import settings


@lru_cache
def admin_client() -> Client:
    if not settings.supabase_url or not settings.supabase_service_key:
        raise RuntimeError(
            "SUPABASE_URL and SUPABASE_SERVICE_KEY must be set in the environment."
        )
    return create_client(settings.supabase_url, settings.supabase_service_key)


def user_client(access_token: str) -> Client:
    if not settings.supabase_url or not settings.supabase_anon_key:
        raise RuntimeError(
            "SUPABASE_URL and SUPABASE_ANON_KEY must be set in the environment."
        )
    client = create_client(settings.supabase_url, settings.supabase_anon_key)
    client.postgrest.auth(access_token)
    return client
