import subprocess
import os
import requests
import asyncio
import aiohttp
from aiohttp.client_exceptions import InvalidURL
import ast
import random
from collections import Counter
from bs4 import BeautifulSoup, SoupStrainer
import streamlit as st

st.set_page_config(
    page_title="Bandcamp Explorer"
)

hide_streamlit_style = """
                <style>
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
    st.session_state['bc_url_input'] = ""

if 'submit_pressed' not in st.session_state:
    st.session_state['submit_pressed'] = False

if 'filter_pressed' not in st.session_state:
    st.session_state['filter_pressed'] = False

if 'selected_tralbums' not in st.session_state:
    st.session_state['selected_tralbums'] = ''

if 'query_title' not in st.session_state:
    st.session_state['query_title'] = ''

if 'query_url' not in st.session_state:
    st.session_state['query_url'] = ''

def button_callback(args):
    st.session_state['bc_url_input'] = args


async def get_info_from_tralbum(session, bc_url):
    try:
        async with session.get(bc_url) as resp:
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
    url_main = bc_url.split('://')[-1].split('/')[0]
    url = 'https://' + url_main + '/api/tralbumcollectors/2/thumbs'
    query_title = soup_meta.find(property="og:title")['content']
    query_tralbum_type = bc_info['item_type']
    query_tralbum_id = bc_info['item_id']
    data = '{"tralbum_type":"' + query_tralbum_type + '","tralbum_id":' + str(query_tralbum_id) + ',"count":500}'
    async with session.post(url, data=data) as resp:
        parsed_response = await resp.json()
    fans = [item['fan_id'] for item in parsed_response['results']]
    if query_tralbum_type == "t":
        async with session.get(bc_url) as resp:
            soup_h3 = BeautifulSoup(await resp.text(), "html.parser", parse_only=SoupStrainer("h3"))
            album_url = 'https://' + url_main + soup_h3.find('a')['href']
    else:
        album_url = None
    return query_title, query_tralbum_type, query_tralbum_id, fans, album_url

async def get_fan_tralbums(session, fan_data, purchase_priority, query_tralbum_id, tralbums_per_fan):
    async with session.post('https://bandcamp.com/api/fancollection/1/collection_items', data=fan_data) as response:
        parsed_response = await response.json()
        tralbums = parsed_response['items']
        desired_keys = ("item_type", "tralbum_id", "item_url", "item_title", "band_name", "num_streamable_tracks")
        tralbums = [{key: dict[key] for key in desired_keys} for dict in tralbums]
        tralbums = [tralbum for tralbum in tralbums if
                    tralbum['tralbum_id'] != query_tralbum_id and tralbum['num_streamable_tracks'] != 0]
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

async def create(bc_url, prioritise_recent_purchasers, purchase_priority, variability):
    async with aiohttp.ClientSession() as session:
        query_url = bc_url
        query_title, query_tralbum_type, query_tralbum_id, fans, album_url = await get_info_from_tralbum(session, bc_url)
        if len(fans) == 0:
            with st.empty():
                st.warning("nobody's bought this release :( try another one")
                if query_tralbum_type == "t":
                    st.info('trying album of the track')
                    query_title, query_tralbum_type, query_tralbum_id, fans, _album_url  = await get_info_from_tralbum(
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

        fans_data = ['{"fan_id":' + str(fan) + ', "older_than_token":"2145916799::t","count":100}' for fan in
                     selected_fans]
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

        html_insert = ''
        for i, tralbum in enumerate(selected_tralbums):
            if tralbum['item_type'] == 'package':
                tralbum['item_type'] = 'album'
            tralbum['tags'] = tralbum_tags[i]
            html_insert += '<iframe style="border: 0; width: 200px; height: 200px;" src="https://bandcamp.com/EmbeddedPlayer/' + \
                           tralbum['item_type'] + '=' + str(tralbum[
                                                                'tralbum_id']) + '/size=large/bgcol=333333/linkcol=0f91ff/minimal=true/transparent=true/" seamless><a href=' + \
                           tralbum['item_url'] + '>' + tralbum['item_title'] + ' by ' + tralbum[
                               'band_name'] + '</a></iframe>'
        return selected_tralbums, query_title, query_url

def generate_html_markdown(selected_tralbums):
    html_insert = ''
    for tralbum in selected_tralbums:
        html_insert += '<iframe style="border: 0; width: 200px; height: 200px;" src="https://bandcamp.com/EmbeddedPlayer/' + \
                       tralbum['item_type'] + '=' + str(tralbum[
                                                            'tralbum_id']) + '/size=large/bgcol=333333/linkcol=0f91ff/minimal=true/transparent=true/" seamless><a href=' + \
                       tralbum['item_url'] + '>' + tralbum['item_title'] + ' by ' + tralbum[
                           'band_name'] + '</a></iframe>'
    return st.markdown(html_insert, unsafe_allow_html=True)

@st.experimental_memo
def filter_tralbums_by_tag(selected_tralbums, selected_tags):
    if selected_tags == []:
        filtered_tralbums = selected_tralbums
    else:
        filtered_tralbums = [tralbum for tralbum in selected_tralbums if
                             len(set(tralbum['tags']).intersection(selected_tags)) > 0]
    return filtered_tralbums


st.title('Bandcamp Explorer :sunglasses:')
st.caption('[contact for bugs/suggestions :)](https://instagram.com/rxniqueh)')
st.caption('*p.s. mobile users: click in top left for a search tool*')

with st.sidebar:
    query = st.text_input(
        "bandcamp search"
    ).replace('+', '2B').replace(' ', '+').replace('&', '%26').replace('=', '%3D').replace('@', '%40').replace("'",
                                                                                                               "%27")
    query_url = "https://bandcamp.com/search?q=" + query
    s = requests.session()
    response = s.get(query_url)
    soup = BeautifulSoup(response.text, "html.parser", parse_only=SoupStrainer("li"))
    results = soup.find_all(class_="searchresult data-search")
    results_data = [{
        'summary_data': ast.literal_eval(item['data-search']),
        'url': item.find('a')['href'].split('?')[0],
        'title': '**' + item.find(class_="result-info").find(class_='heading').get_text(strip=True) + '**'
                 + ' '
                 + '*' +  ' '.join([elem for elem in
                             item.find(class_="result-info").find(class_='subhead').get_text(strip=True).replace('\n',
                                                                                                                 '').split(
                                 ' ') if elem != '']) + '*'
    } for item in results]
    results_data = [dict for dict in results_data if dict['summary_data']['type'] in ('a', 't')]
    if len(results_data) == 0 and query_url != "https://bandcamp.com/search?q=":
        st.write("no results found, try something different")
    for result in results_data:
        st.button(result['title'], key=result['url'], type="primary", on_click=button_callback, args=(result['url'],))

input_form = st.form("input_form")
bc_url = input_form.text_input('what bandcamp release do you want to explore?',
                               help='url of bandcamp release (track or album)', key='bc_url_input')
prioritise_recent_purchasers = input_form.radio('prioritise recent purchasers?', ('no', 'yes'),
                                                help='yes:  recent purchasers of the release \n \n no: random purchasers of the release')
purchase_priority = input_form.radio("what would you like to prioritise in purchases?", ('random', 'recent', 'top'),
                                     help='random: random purchases from the chosen purchasers  \n \n recent: recent purchases from the chosen purchasers \n \n top: releases that are commonly found in random purcharsers purchases. set wildness higher for better results. might be slow')
variability = [18, 12, 9, 6, 4, 3, 2, 1][input_form.slider('wildness', 1, 8, 1) - 1]
submitted = input_form.form_submit_button("Submit")
if submitted and st.session_state['filter_pressed']:
    st.session_state['filter_pressed'] = False
    st.session_state['query_title'] = ''
    st.session_state['selected_tralbums'] = ''

if submitted and not st.session_state['filter_pressed']:
    st.session_state['submit_pressed'] = True
    with st.spinner(text='hold on, goodness incoming :)'):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        selected_tralbums, query_title, query_url = loop.run_until_complete(create(bc_url, prioritise_recent_purchasers, purchase_priority, variability))
        st.session_state['selected_tralbums'] = selected_tralbums
        st.session_state['query_title'] = query_title
        st.session_state['query_url'] = query_url

if st.session_state['submit_pressed'] or st.session_state['filter_pressed']:
    query_title = st.session_state['query_title']
    selected_tralbums = st.session_state['selected_tralbums']
    query_url = st.session_state['query_url']

    if prioritise_recent_purchasers == 'yes':
        purchasers = 'recent'
    else:
        purchasers = 'random'
    if purchase_priority == 'top':
        subtitle_markdown = 'purchases commonly found in ' + purchasers + ' purchasers of [' + query_title + "](" + query_url + ")"
    else:
        subtitle_markdown = purchase_priority + " purchases of " + purchasers + " purchasers of [" + query_title + "](" + query_url + ")"
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
else:
    st.stop()

