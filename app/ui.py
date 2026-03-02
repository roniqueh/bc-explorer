import streamlit as st
from streamlit.components.v1 import html

CUSTOM_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Syne:wght@400;700&display=swap');

html, body, div, label [class*="css"]  {
font-family: 'Syne', sans-serif;
}

section.main {
background-color:hsla(15,100%,80%,0);
background-image:
url("https://www.transparenttextures.com/patterns/otis-redding.png"),
radial-gradient(at 55% 17%, hsla(43,71%,37%,1) 0px, transparent 50%),
radial-gradient(at 27% 78%, hsla(187,71%,37%,1) 0px, transparent 50%),
radial-gradient(at 94% 10%, hsla(24,71%,37%,1) 0px, transparent 50%),
radial-gradient(at 21% 1%, hsla(332,71%,37%,1) 0px, transparent 50%),
radial-gradient(at 7% 96%, hsla(183,71%,37%,1) 0px, transparent 50%),
radial-gradient(at 95% 32%, hsla(263,71%,37%,1) 0px, transparent 50%),
radial-gradient(at 53% 81%, hsla(33,71%,37%,1) 0px, transparent 50%);
}

.block-container {
padding-top: 2rem;
}

div[data-testid="stCaptionContainer"] {
text-align: right;
}

div[data-testid="stForm"] {
background-color: rgba(0, 0, 0, .10);
backdrop-filter: blur(16px);
}

h1 {
font-weight:700;
font-size:3rem;
}

section[data-testid="stSidebar"] div.stButton button {
width: 100%;
}

div[data-testid="stToolbar"] {
visibility: hidden;
height: 0%;
position: fixed;
}

div[data-testid="stDecoration"] {
visibility: hidden;
height: 0%;
position: fixed;
}
div[data-testid="stStatusWidget"] {
visibility: hidden;
height: 0%;
position: fixed;
}
#MainMenu {
visibility: hidden;
height: 0%;
}
header {
visibility: hidden;
height: 0%;
}
footer {
visibility: hidden;
height: 0%;
}
</style>
"""

BMC_BUTTON_HTML = """
<script type="text/javascript"
    src="https://cdnjs.buymeacoffee.com/1.0.0/button.prod.min.js"
    data-name="bmc-button"
    data-slug="bc.explorer"
    data-color="#FFDD00"
    data-emoji=""
    data-font="Cookie"
    data-text="Buy me a coffee"
    data-outline-color="#000000"
    data-font-color="#000000"
    data-coffee-color="#000000" >
</script>
"""


def apply_custom_styles():
    st.markdown(CUSTOM_CSS, unsafe_allow_html=True)


def render_bmc_button():
    html(BMC_BUTTON_HTML, width=220, height=84)


def render_results(tralbums: list) -> None:
    html_list = []
    for tralbum in tralbums:
        item_type = 'album' if tralbum['item_type'] == 'package' else tralbum['item_type']
        html_list.append(
            f'<iframe style="border: 0; width: 200px; height: 200px;" '
            f'src="https://bandcamp.com/EmbeddedPlayer/{item_type}={tralbum["tralbum_id"]}'
            f'/size=large/bgcol=333333/linkcol=0f91ff/minimal=true/transparent=true/" seamless>'
            f'<a href={tralbum["item_url"]}>{tralbum["item_title"]} by {tralbum["band_name"]}</a>'
            f'</iframe>'
        )
    html_insert = '<div class="results-container" style="text-align: center;">\n' + "\n".join(html_list) + '\n</div>'
    st.markdown(html_insert, unsafe_allow_html=True)


@st.cache_data(max_entries=50)
def filter_tralbums_by_tag(selected_tralbums: tuple, selected_tags: tuple) -> list:
    """Filter tralbums by tags. Accepts tuples for hashability with st.cache_data."""
    if not selected_tags:
        return list(selected_tralbums)
    return [t for t in selected_tralbums if set(t['tags']).intersection(selected_tags)]
