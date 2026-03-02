import asyncio

import streamlit as st
from human_id import generate_id

from app.config import DEFAULT_BC_URL, FRESHNESS_MAP, SUPABASE_ENABLED, WILDNESS_MAP
from app.database import load_shared_result, save_result
from app.scraper import InvalidBandcampURL, NoFansFound, discover
from app.search import search_bandcamp
from app.ui import apply_custom_styles, filter_tralbums_by_tag, render_bmc_button, render_results

# ---------------------------------------------------------------------------
# Page setup
# ---------------------------------------------------------------------------

st.set_page_config(page_title="Bandcamp Explorer")
st.caption("[contact for bugs/suggestions :)](https://instagram.com/rxniqueh)")
st.title("BANDCAMP EXPLORER")
apply_custom_styles()
render_bmc_button()

# ---------------------------------------------------------------------------
# Session state
# ---------------------------------------------------------------------------

_state_defaults = {
    "bc_url_input": DEFAULT_BC_URL,
    "submit_pressed": False,
    "filter_pressed": False,
    "query_params_loaded": False,
    "results_dict": {
        "uid": "",
        "data": {"query_title": "", "query_url": "", "selected_tralbums": None},
    },
}
for key, default in _state_defaults.items():
    if key not in st.session_state:
        st.session_state[key] = default

# ---------------------------------------------------------------------------
# Shared result loading (via ?id= query param + Supabase)
# ---------------------------------------------------------------------------

def _load_from_query_params():
    uid = st.query_params.get("id")
    if not uid or not SUPABASE_ENABLED:
        return
    data = load_shared_result(uid)
    if data is not None:
        st.session_state["results_dict"]["uid"] = uid
        st.session_state["results_dict"]["data"].update(data)
        st.session_state["submit_pressed"] = True
        st.session_state["query_params_loaded"] = True
        st.session_state["bc_url_input"] = data["query_url"]


if not st.session_state["submit_pressed"] and not st.session_state["query_params_loaded"]:
    _load_from_query_params()

# ---------------------------------------------------------------------------
# Callbacks
# ---------------------------------------------------------------------------

def _on_search_change():
    st.session_state["submit_pressed"] = False
    st.session_state["filter_pressed"] = False


def _on_result_click(url: str):
    st.session_state["submit_pressed"] = False
    st.session_state["filter_pressed"] = False
    st.session_state["bc_url_input"] = url

# ---------------------------------------------------------------------------
# Sidebar search
# ---------------------------------------------------------------------------

with st.sidebar:
    query = st.text_input("bandcamp search", on_change=_on_search_change)
    if query:
        results = search_bandcamp(query)
        if not results:
            st.write("no results found, try something different")
        for result in results:
            st.button(
                result["title"],
                key=result["url"],
                type="secondary",
                on_click=_on_result_click,
                args=(result["url"],),
            )

# ---------------------------------------------------------------------------
# Input form
# ---------------------------------------------------------------------------

input_form = st.form("input_form")
bc_url = input_form.text_input(
    "what bandcamp release do you want to explore?",
    help="url of bandcamp release (track or album)",
    key="bc_url_input",
    value=st.session_state["bc_url_input"],
)
input_form.caption("*p.s. mobile users: click arrow in top left for a search tool*")
prioritise_recent = input_form.radio(
    "prioritise recent purchasers?",
    options=[False, True],
    format_func=lambda v: "yes" if v else "no",
    help="yes: recent purchasers of the release\n\nno: random purchasers of the release",
) or False
purchase_priority = input_form.radio(
    "what would you like to prioritise in purchases?",
    ("random", "recent", "top"),
    help=(
        "random: random purchases from the chosen purchasers\n\n"
        "recent: recent purchases from the chosen purchasers\n\n"
        "top: releases commonly found in purchasers' collections. "
        "set wildness higher/freshness lower for better results."
    ),
)
variability = WILDNESS_MAP[input_form.slider("wildness", 1, 8, 5, help="higher values looks at purchases from more users") - 1]
freshness = FRESHNESS_MAP[input_form.slider("freshness", 1, 8, 5, help="higher values looks at more recent purchase histories of users") - 1]
submitted = input_form.form_submit_button("submit")

# ---------------------------------------------------------------------------
# State transitions
# ---------------------------------------------------------------------------

if submitted and st.session_state["filter_pressed"]:
    st.session_state["filter_pressed"] = False
    st.session_state["results_dict"]["data"]["query_title"] = ""
    st.session_state["results_dict"]["data"]["selected_tralbums"] = None

if submitted and not st.session_state["filter_pressed"]:
    st.session_state["submit_pressed"] = True
    st.session_state["query_params_loaded"] = False
    bc_url = st.session_state["bc_url_input"]

    with st.spinner("hold on, goodness incoming :)"):
        try:
            selected_tralbums, query_title, query_url = asyncio.run(
                discover(bc_url, prioritise_recent, purchase_priority, variability, freshness)
            )
        except InvalidBandcampURL:
            st.warning(
                "this needs to be a bandcamp release link. "
                "to search releases and automatically input links, use the sidebar on the left"
            )
            st.stop()
        except NoFansFound:
            st.warning("nobody's bought this release :( try another one")
            st.stop()

    st.session_state["results_dict"]["data"]["selected_tralbums"] = selected_tralbums
    st.session_state["results_dict"]["data"]["query_title"] = query_title
    st.session_state["results_dict"]["data"]["query_url"] = query_url

    if SUPABASE_ENABLED:
        uid = generate_id()
        st.session_state["results_dict"]["uid"] = uid
        st.session_state["query_params_loaded"] = False
        save_result(uid, st.session_state["results_dict"]["data"])

# ---------------------------------------------------------------------------
# Results display
# ---------------------------------------------------------------------------

if st.session_state["submit_pressed"] or st.session_state["filter_pressed"]:
    results_dict = st.session_state["results_dict"]
    query_title = results_dict["data"]["query_title"]
    selected_tralbums = results_dict["data"]["selected_tralbums"]
    query_url = results_dict["data"]["query_url"]

    if SUPABASE_ENABLED and results_dict["uid"]:
        st.query_params["id"] = results_dict["uid"]

    purchasers = "recent" if prioritise_recent else "random"
    if purchase_priority == "top":
        subtitle = f"purchases commonly found in {purchasers} purchasers of [{query_title}]({query_url})"
    else:
        subtitle = f"{purchase_priority} purchases of {purchasers} purchasers of [{query_title}]({query_url})"
    st.markdown(subtitle)

    all_tags = sorted({tag for t in selected_tralbums for tag in t["tags"]})
    filter_form = st.form("filter_form")
    selected_tags = filter_form.multiselect("filter tags", all_tags)
    filtered = filter_form.form_submit_button("filter")

    if filtered:
        st.session_state["filter_pressed"] = True
        display_tralbums = filter_tralbums_by_tag(tuple(selected_tralbums), tuple(selected_tags))
    else:
        display_tralbums = selected_tralbums

    render_results(display_tralbums)
    st.session_state["query_params_loaded"] = True

else:
    st.session_state["submit_pressed"] = False
    st.session_state["filter_pressed"] = False
    st.stop()
