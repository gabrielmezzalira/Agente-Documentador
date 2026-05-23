from supabase import create_client, Client
import os


def get_client() -> Client:
    """Lazy Supabase client factory.

    Reads SUPABASE_URL and SUPABASE_SERVICE_KEY from os.environ at call time,
    not at import time — env vars may not be loaded yet when the module is imported.
    """
    return create_client(
        os.environ["SUPABASE_URL"],
        os.environ["SUPABASE_SERVICE_KEY"],
    )
