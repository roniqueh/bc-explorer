import os

# Results
MAX_RESULTS = 36

# Bandcamp API
FANS_ENDPOINT = "/api/tralbumcollectors/2/thumbs"
COLLECTION_ENDPOINT = "https://bandcamp.com/api/fancollection/1/collection_items"
BANDCAMP_SEARCH_URL = "https://bandcamp.com/search?q="
COLLECTION_TOKEN = "2145916799::t"

# UI defaults
DEFAULT_BC_URL = "https://tobagotracks.bandcamp.com/album/fantasias-for-lock-in"
WILDNESS_MAP = [18, 12, 9, 6, 4, 3, 2, 1]
FRESHNESS_MAP = [1024, 512, 256, 128, 64, 32, 16, 8]

# Supabase (optional — sharing feature disabled if not set)
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
SUPABASE_ENABLED = bool(SUPABASE_URL and SUPABASE_KEY)
