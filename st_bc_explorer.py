import subprocess
import os
import requests
import ast
import random
from collections import Counter
from bs4 import BeautifulSoup, SoupStrainer
import streamlit as st

st.title('Bandcamp Explorer :sunglasses:')
st.markdown('[contact for bugs/suggestions :)](https://instagram.com/rxniqueh)')

with st.form("input_form"):
    bc_url = st.text_input('what bandcamp release do you want to explore?',
                           help='url of bandcamp release (track or album)')
    prioritise_recent_purchasers = st.radio('prioritise recent purchasers?', ('no', 'yes'), help='yes: the most recent purchasers of the release \n \n no: random purchasers of the release')
    purchase_priority = st.radio("what would you like to prioritise in purchases?", ('random', 'recent', 'top'), help='random: random purchases from the chosen purchasers  \n \n recent: recent purchases from the chosen purchasers \n \n top: releases that are commonly found in the chosen purcharsers purchases. set variability higher for better results. might be slow' )
    variability = [18, 12, 9, 6, 4, 3, 2, 1][st.slider('from 1-8, how much variability?', 1, 8, 1, help='go on, slide it to the right. make take longer') - 1]
    submitted = st.form_submit_button("Submit")

if bc_url != '':
    with st.spinner(text='hold on, goodness incoming :)'):
        page = requests.get(bc_url)
        soup = BeautifulSoup(page.text, "html.parser", parse_only=SoupStrainer("meta"))
        try:
            bc_info = ast.literal_eval(soup.find(attrs={"name": "bc-page-properties"})['content'])
        except TypeError:
            st.warning("please try a bandcamp release link")
            st.stop()
        url_prefix = bc_url.split(".com/")[0]
        url = url_prefix + '.com/api/tralbumcollectors/2/thumbs'
        query_title = soup.find(property="og:title")['content']
        query_tralbum_type = bc_info['item_type']
        query_tralbum_id = bc_info['item_id']
        data = '{"tralbum_type":"' + query_tralbum_type + '","tralbum_id":' + str(query_tralbum_id) + ',"count":500}'
        response = requests.post(url, data=data)
        parsed_response = response.json()
        fans = parsed_response['results']
        if len(fans) == 0:
            st.warning("nobody's bought this release :( try another one")
            st.stop()
        if prioritise_recent_purchasers == 'yes':
            selected_fans = fans[:min(36 // variability, len(fans))]
        else:
            selected_fans = random.sample(fans, min(36 // variability, len(fans)))
        tralbums_per_fan = 36 // len(selected_fans)

        selected_tralbums = []
        for fan in selected_fans:
            url = 'https://bandcamp.com/api/fancollection/1/collection_items'
            data = '{"fan_id":' + str(fan['fan_id']) + ', "older_than_token":"2145916799::t","count":100}'
            response = requests.post(url, data=data)
            parsed_response = response.json()
            tralbums = parsed_response['items']
            desired_keys = ["item_type", "tralbum_id", "item_url", "item_title", "band_name"]
            tralbums = [{key: dict[key] for key in desired_keys} for dict in tralbums]
            tralbums = [tralbum for tralbum in tralbums if tralbum['tralbum_id'] != query_tralbum_id]
            if purchase_priority == 'top':
                selected_tralbums += tralbums
            elif purchase_priority == 'recent':
                selected_tralbums += tralbums[:min(tralbums_per_fan, len(tralbums))]
            else:
                selected_tralbums += random.sample(tralbums, min(tralbums_per_fan, len(tralbums)))

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

        html_insert = ''
        for tralbum in selected_tralbums:
            if tralbum['item_type'] == 'package':
                tralbum['item_type'] = 'album'
            html_insert += '<iframe style="border: 0; width: 200px; height: 200px;" src="https://bandcamp.com/EmbeddedPlayer/' + \
                           tralbum['item_type'] + '=' + str(tralbum[
                                                                'tralbum_id']) + '/size=large/bgcol=333333/linkcol=0f91ff/minimal=true/transparent=true/" seamless><a href=' + \
                           tralbum['item_url'] + '>' + tralbum['item_title'] + ' by ' + tralbum[
                               'band_name'] + '</a></iframe>'

        subtitle_markdown = "results for: [" + query_title + "](" + bc_url + ")"
        st.markdown(subtitle_markdown)
        st.markdown(html_insert, unsafe_allow_html=True)
        st.success('enjoy!')
else:
    st.stop()
