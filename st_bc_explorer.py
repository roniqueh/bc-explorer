from datetime import datetime
import requests
import asyncio
import aiohttp
from aiohttp.client_exceptions import InvalidURL
import ast
import random
from collections import Counter
from bs4 import BeautifulSoup, SoupStrainer
from human_id import generate_id
from supabase import create_client, Client
import streamlit as st


st.set_page_config(
    page_title="Bandcamp Explorer"
)

st.caption('[contact for bugs/suggestions :)](https://instagram.com/rxniqueh)')
st.title('BANDCAMP EXPLORER')

hide_streamlit_style = """
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

st.markdown(hide_streamlit_style, unsafe_allow_html=True)

if 'bc_url_input' not in st.session_state:
    st.session_state['bc_url_input'] = "https://tobagotracks.bandcamp.com/album/fantasias-for-lock-in"

if 'submit_pressed' not in st.session_state:
    st.session_state['submit_pressed'] = False

if 'filter_pressed' not in st.session_state:
    st.session_state['filter_pressed'] = False

if 'results_dict' not in st.session_state:
    st.session_state['results_dict'] = {"uid": "",
                                        "data": {"query_title": "", "query_url": "", "selected_tralbums": None}}

if 'query_params_loaded' not in st.session_state:
    st.session_state['query_params_loaded'] = False


@st.experimental_singleton
def init_connection():
    url = st.secrets["supabase_url"]
    key = st.secrets["supabase_key"]
    return create_client(url, key)


supabase = init_connection()


def run_id_query(uid):
    row = supabase.table("resultstable").select("data").eq("uid", uid).limit(1).execute()
    try:
        return row.data[0]['data']
    except IndexError:
        return None


def load_query_params():
    try:
        uid = st.experimental_get_query_params()['id'][0]
        data = run_id_query(uid)
        if data is not None:
            st.session_state['results_dict']['uid'] = uid
            for key in data:
                st.session_state['results_dict']['data'][key] = data[key]
            st.session_state['submit_pressed'] = True
            st.session_state['query_params_loaded'] = True
            st.session_state['bc_url_input'] = st.session_state['results_dict']['data']['query_url']
    except KeyError:
        pass
        

if not st.session_state['submit_pressed'] and not st.session_state['query_params_loaded']:
    load_query_params()


def insert_data(results_dict):
    if not st.session_state['query_params_loaded']:
        supabase.table("resultstable").insert({'uid': results_dict['uid'], 'data': results_dict['data']}).execute()

def search_input_callback():
    st.session_state['submit_pressed'] = False
    st.session_state['filter_pressed'] = False

def button_callback(url):
    st.session_state['submit_pressed'] = False
    st.session_state['filter_pressed'] = False
    st.session_state['bc_url_input'] = url


async def get_info_from_tralbum(session, input_url):
    try:
        async with session.get(input_url) as resp:
            soup_meta = BeautifulSoup(await resp.text(), "html.parser", parse_only=SoupStrainer("meta"))
        try:
            bc_info = ast.literal_eval(soup_meta.find(attrs={"name": "bc-page-properties"})['content'])
        except TypeError:
            st.warning("please try a bandcamp release link")
            st.stop()
    except InvalidURL:
        st.warning(
            "this needs to be a bandcamp release link. to search releases and automatically input links, use the sidebar on the left")
        st.stop()
    url_main = input_url.split('://')[-1].split('/')[0]
    url = f"https://{url_main}/api/tralbumcollectors/2/thumbs"
    query_title = soup_meta.find(property="og:title")['content']
    query_tralbum_type = bc_info['item_type']
    query_tralbum_id = bc_info['item_id']
    data = '{{"tralbum_type":"{}", "tralbum_id":"{}", "count":500}}'.format(query_tralbum_type, query_tralbum_id)
    async with session.post(url, data=data) as resp:
        parsed_response = await resp.json()
    fans = [{
        "fan_id": item['fan_id'],
        "mod_date": datetime.strptime(item['mod_date'], "%d %b %Y %H:%M:%S %Z")
    } for item in parsed_response['results']]
    if query_tralbum_type == "t":
        async with session.get(bc_url) as resp:
            soup_h3 = BeautifulSoup(await resp.text(), "html.parser", parse_only=SoupStrainer("h3"))
            album_url = f"https://{url_main}{soup_h3.find('a')['href']}"
    else:
        album_url = None
    return query_title, query_tralbum_type, query_tralbum_id, fans, album_url


async def get_fan_tralbums(session, fan_data, purchase_priority, query_tralbum_id, tralbums_per_fan):
    async with session.post('https://bandcamp.com/api/fancollection/1/collection_items', data=fan_data) as response:
        parsed_response = await response.json()
        tralbums = parsed_response['items']
        desired_keys = (
            "item_type", "tralbum_id", "item_url", "item_title", "band_name", "num_streamable_tracks",
            "is_subscriber_only")
        tralbums = [{key: dict[key] for key in desired_keys} for dict in tralbums]
        tralbums = [tralbum for tralbum in tralbums if
                    tralbum['tralbum_id'] != query_tralbum_id and tralbum['num_streamable_tracks'] != 0 and tralbum[
                        "is_subscriber_only"] == False]
        if purchase_priority == 'top':
            selected_tralbums = tralbums
        elif purchase_priority == 'recent':
            selected_tralbums = tralbums[:tralbums_per_fan]
        else:
            selected_tralbums = random.sample(tralbums, min(tralbums_per_fan, len(tralbums)))
        return selected_tralbums


async def get_tralbum_tags(session, item_url):
    async with session.get(item_url) as resp:
        soup = BeautifulSoup(await resp.text(), "html.parser", parse_only=SoupStrainer("a"))
        tags = [item.text for item in soup.find_all(class_="tag")]
        return tags


async def create(bc_url, prioritise_recent_purchasers, purchase_priority, variability, freshness):
    async with aiohttp.ClientSession() as session:
        query_url = bc_url
        query_title, query_tralbum_type, query_tralbum_id, fans, album_url = await get_info_from_tralbum(session,
                                                                                                         bc_url)
        if len(fans) == 0:
            with st.empty():
                st.warning("nobody's bought this release :( try another one")
                if query_tralbum_type == "t":
                    st.info('trying album of the track')
                    query_title, query_tralbum_type, query_tralbum_id, fans, _album_url = await get_info_from_tralbum(
                        session, album_url)
                    if len(fans) > 0:
                        st.success("using album instead of track")
                        query_url = album_url
                    else:
                        st.warning("no luck again, sorry :(")
                        st.stop()
                else:
                    st.stop()
        if prioritise_recent_purchasers == 'yes':
            selected_fans = fans[:36 // variability]
        else:
            selected_fans = random.sample(fans, min(36 // variability, len(fans)))
        tralbums_per_fan = 36 // len(selected_fans)

        fans_data = ['{{"fan_id":{0}, "older_than_token":"2145916799::t","count":{1}}}'.format(fan['fan_id'], freshness)
                     for fan in selected_fans]
        tasks = []
        for fan_data in fans_data:
            tasks.append(get_fan_tralbums(session, fan_data, purchase_priority, query_tralbum_id, tralbums_per_fan))
        selected_tralbums = await asyncio.gather(*tasks)
        selected_tralbums = [item for list in selected_tralbums for item in list]
        if purchase_priority == 'top':
            most_common_tralbums = Counter(item['tralbum_id'] for item in selected_tralbums).most_common(36)
            mct_ids = [item[0] for item in most_common_tralbums]
            freq = [item[1] for item in most_common_tralbums]
            seen = set()
            filtered_list = []
            for tralbum in selected_tralbums:
                if tralbum['tralbum_id'] in mct_ids and tralbum['tralbum_id'] not in seen:
                    filtered_list.append(tralbum)
                    seen.add(tralbum['tralbum_id'])
            selected_tralbums = filtered_list
        tasks = []
        for tralbum in selected_tralbums:
            tasks.append(get_tralbum_tags(session, tralbum['item_url']))
        tralbum_tags = await asyncio.gather(*tasks)
        for i, tralbum in enumerate(selected_tralbums):
            tralbum['tags'] = tralbum_tags[i]
        return selected_tralbums, query_title, query_url


def generate_html_markdown(selected_tralbums):
    html_list = []
    for tralbum in selected_tralbums:
        item_type = 'album' if tralbum['item_type'] == 'package' else tralbum['item_type']
        html_list.append(
            f'<iframe style="border: 0; width: 200px; height: 200px;" src="https://bandcamp.com/EmbeddedPlayer/{item_type}={tralbum["tralbum_id"]}/size=large/bgcol=333333/linkcol=0f91ff/minimal=true/transparent=true/" seamless><a href={tralbum["item_url"]}>{tralbum["item_title"]} by {tralbum["band_name"]}</a></iframe>')
    html_insert = '<div class="results-container" style="text-align: center;">\n' + "\n".join(html_list) + '\n</div>'
    return st.markdown(html_insert, unsafe_allow_html=True)


@st.experimental_memo(max_entries=50)
def filter_tralbums_by_tag(selected_tralbums, selected_tags):
    if selected_tags == []:
        filtered_tralbums = selected_tralbums
    else:
        filtered_tralbums = [tralbum for tralbum in selected_tralbums if
                             len(set(tralbum['tags']).intersection(selected_tags)) > 0]
    return filtered_tralbums


with st.sidebar:
    query = st.text_input("bandcamp search", on_change=search_input_callback)
    query = query.translate(str.maketrans({'+': '2B', ' ': '+', '&': '%26', '=': '%3D', '@': "%40", "'": "%27"}))
    query_url = "https://bandcamp.com/search?q=" + query
    s = requests.session()
    response = s.get(query_url)
    soup = BeautifulSoup(response.text, "html.parser", parse_only=SoupStrainer("li"))
    results = soup.find_all(class_="searchresult data-search")
    results_data = [{'summary_data': ast.literal_eval(item['data-search']),
                     'url': item.find('a')['href'].split('?')[0],
                     'title': '**{}** *{}*'.format(
                         item.find(class_="result-info").find(class_='heading').get_text(strip=True),
                         ' '.join([elem for elem in
                                   item.find(class_="result-info").find(class_='subhead').get_text(strip=True).replace(
                                       '\n', '').split(' ') if elem != ''])
                     ),
                     }
                    for item in results
                    ]
    results_data = [dict for dict in results_data if dict['summary_data']['type'] in ('a', 't')]
    if len(results_data) == 0 and query_url != "https://bandcamp.com/search?q=":
        st.write("no results found, try something different")
    for result in results_data:
        st.button(result['title'], key=result['url'], type="secondary", on_click=button_callback, args=(result['url'],))

input_form = st.form("input_form")
bc_url = input_form.text_input('what bandcamp release do you want to explore?',
                               help='url of bandcamp release (track or album)', key='bc_url_input',
                               value=st.session_state['bc_url_input'])
input_form.caption('*p.s. mobile users: click arrow in top left for a search tool*')
prioritise_recent_purchasers = input_form.radio('prioritise recent purchasers?', ('no', 'yes'),
                                                help='yes:  recent purchasers of the release \n \n no: random purchasers of the release')
purchase_priority = input_form.radio("what would you like to prioritise in purchases?", ('random', 'recent', 'top'),
                                     help='random: random purchases from the chosen purchasers  \n \n recent: recent purchases from the chosen purchasers \n \n top: releases that are commonly found in random purcharsers purchases. set wildness higher/freshness lower for better results. might be slow')
variability = [18, 12, 9, 6, 4, 3, 2, 1][
    input_form.slider('wildness', 1, 8, 5, help='higher values looks at purchases from more users') - 1]
freshness = [1024, 512, 256, 128, 64, 32, 16, 8][input_form.slider('freshness', 1, 8, 5,
                                                                   help="higher values looks at more recent purchase histories of users \n \n won't change results much if recent purchases prioritised") - 1]
submitted = input_form.form_submit_button("submit")

# reset for a new search made after filtering the previous search
if submitted and st.session_state['filter_pressed']:
    st.session_state['filter_pressed'] = False
    st.session_state['results_dict']['data']['query_title'] = ''
    st.session_state['results_dict']['data']['selected_tralbums'] = None

# main processing
if submitted and not st.session_state['filter_pressed']:
    st.session_state['submit_pressed'] = True
    st.session_state['query_params_loaded'] = False
    bc_url = st.session_state['bc_url_input']
    with st.spinner(text='hold on, goodness incoming :)'):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        selected_tralbums, query_title, query_url = loop.run_until_complete(
            create(bc_url, prioritise_recent_purchasers, purchase_priority, variability, freshness))
        st.session_state['results_dict']['data']['selected_tralbums'] = selected_tralbums
        st.session_state['results_dict']['data']['query_title'] = query_title
        st.session_state['results_dict']['data']['query_url'] = query_url
        st.session_state['results_dict']['uid'] = generate_id()
        st.session_state['query_params_loaded'] = False
        insert_data(st.session_state['results_dict'])

# so you can repeatedly filter a current search without repeating above processing
if st.session_state['submit_pressed'] or st.session_state['filter_pressed']:
    results_dict = st.session_state['results_dict']
    # st.write(results_dict)
    st.experimental_set_query_params(id=results_dict['uid'])
    query_title = results_dict['data']['query_title']
    selected_tralbums = results_dict['data']['selected_tralbums']
    query_url = results_dict['data']['query_url']
    purchasers = 'recent' if prioritise_recent_purchasers == 'yes' else 'random'
    subtitle_markdown = (f'{purchase_priority} purchases of {purchasers} purchasers of '
                         f'[{query_title}]({query_url})' if purchase_priority != 'top' else
                         f'purchases commonly found in {purchasers} purchasers of [{query_title}]({query_url})')

    st.markdown(subtitle_markdown)
    all_tags = sorted(list(set([tag for tralbum in selected_tralbums for tag in tralbum['tags']])))
    filter_form = st.form("filter_form")
    selected_tags = filter_form.multiselect('filter tags', all_tags)
    filtered = filter_form.form_submit_button("filter")
    if filtered:
        st.session_state['filter_pressed'] = True
        filtered_tralbums = filter_tralbums_by_tag(selected_tralbums, selected_tags)
        generate_html_markdown(filtered_tralbums)
    else:
        generate_html_markdown(selected_tralbums)
    st.session_state['query_params_loaded'] = True
else:
    st.session_state['submit_pressed'] = False
    st.session_state['filter_pressed'] = False
    st.stop()
