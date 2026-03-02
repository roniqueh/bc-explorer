from app.config import SUPABASE_ENABLED, SUPABASE_URL, SUPABASE_KEY

_client = None


def get_client():
    global _client
    if not SUPABASE_ENABLED:
        return None
    if _client is None:
        from supabase import create_client
        _client = create_client(SUPABASE_URL, SUPABASE_KEY)
    return _client


def load_shared_result(uid: str) -> dict | None:
    """Load a previously shared result by UID. Returns None if DB unavailable or not found."""
    client = get_client()
    if client is None:
        return None
    row = client.table("resultstable").select("data").eq("uid", uid).limit(1).execute()
    try:
        return row.data[0]["data"]
    except (IndexError, KeyError):
        return None


def save_result(uid: str, data: dict) -> bool:
    """Save a result for sharing. Returns False if DB unavailable."""
    client = get_client()
    if client is None:
        return False
    client.table("resultstable").insert({"uid": uid, "data": data}).execute()
    return True
