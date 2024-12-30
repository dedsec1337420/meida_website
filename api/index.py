from flask import Flask, render_template
from flask import request
from flask import jsonify
import httpx
import re
import json
from base64 import b64decode
from base64 import b64encode

#global shit
USER_AGENT:str = 'Mozilla/5.0 (X11; Linux x86_64; rv:133.0) Gecko/20100101 Firefox/133.0'

POP_MAIN_URL:str ="https://popcornmovies.to"
ANIME_URL:str ="https://allanime.day"
ANIME_REF:str = "https://allmanga.to"
ANIME_API:str = "https://api.allanime.day"
AUTO_CDN:str = "https://tom.autoembed.cc"


#streaming stuff
def autoembed_scrapper(url:str,headers:dict)->str:
    r = httpx.get(
        url,
        headers=headers,
        timeout=None
    )

    if r.status_code == 200:
        data = r.json()
        streaming_link = data.get("videoSource",None)
        subtitle = next((s['file'] for s in data.get('subtitles', []) if "English" in s['label']), None)

        return streaming_link,subtitle

def get_tmdb(url:str)->str:
    r = httpx.get(
            url,
            headers={"User-Agent":USER_AGENT},
            timeout=None
            )
    tmdb = re.findall(r'\s+tmdbId:\s+&#039;(\d+)&#039;',r.text)[0]

    return tmdb

def anime_episode(id:str)->list:
    episodes_list_gql = """
    query ($showId: String!) {
        show(_id: $showId) {
            _id
            availableEpisodesDetail
        }
    }
    """
    variables = {"showId":id}

    payload = {
            "variables" : json.dumps(variables),
            "query" : episodes_list_gql
 
            }

    r = httpx.get(
            f"{ANIME_API}/api",
            headers={
                "User-Agent" : USER_AGENT,
                "Referer" : ANIME_REF

                },
            params = payload,
            timeout = None

            )
    ep_count = r.json()["data"]["show"]["availableEpisodesDetail"]["sub"]
    return ep_count if len(ep_count) > 0 else None

def anime_scrapper(id:str,episode:str)->str:
    def dec_link(enc_link)->str:
        decrypted = bytearray()
        for segment in bytearray.fromhex(enc_link):
            decrypted.append(segment ^ 56)
        return decrypted.decode("utf-8")

    episode_embed_gql = """
    query ($showId: String!, $translationType: VaildTranslationTypeEnumType!, $episodeString: String!) {
        episode(
            showId: $showId
            translationType: $translationType
            episodeString: $episodeString
        ) {
            episodeString
            sourceUrls
        }
    }
    """
    variables = {
            "showId": id,
            "translationType": "sub",
            "episodeString" : f"{episode}"

            }
    payload = {
            "variables" : json.dumps(variables),
            "query" : episode_embed_gql
            }

    r = httpx.get(
            f"{ANIME_API}/api",
            headers={
                "User-Agent" : USER_AGENT,
                "Referer" : ANIME_REF
                },
            params = payload,
            timeout=None
            )
    
    

    if r.status_code == 200:
        #print(r.json())
        
        for i in r.json()["data"]["episode"]["sourceUrls"]:
            if i['sourceName'] == 'S-mp4':
                smp4_encrypted_link = i['sourceUrl'][2:]


        #smp4_encrypted_link = re.findall(r'"sourceUrl":"--(.*?)","priority":.*?,"sourceName":"S-mp4"',r.text)[0]
        #print(smp4_encrypted_link)
        smp4_link = dec_link(smp4_encrypted_link)
        #print(smp4_link)
        r = httpx.get(
                f"{ANIME_URL}{smp4_link.replace('clock', 'clock.json')}",
                headers={
                    "User-Agent" : USER_AGENT,
                    "Referer" : ANIME_REF
                    }
                )
        link = r.json()["links"][0]["link"]

        #print(link)

       
        return link



#search functions
def pop_search(media_type:str,query:str)->list:
    r=httpx.get(f"{POP_MAIN_URL}/search/{query.replace(" ", "%20")}",headers={'User-Agent': USER_AGENT})

    if r.status_code == 200:
        results = re.findall(r'<div class=\"relative group overflow-hidden\">\s+<a href=\"(.*?)\"\s+class=".*?">\s+<picture>\s+<img .+? data-src="(.*?)" alt="(.*?)"',r.text)

        if media_type == "movie":
            search_result= [r for r in results if "/movie/" in r[0]]
        else:
            search_result = [r for r in results if "/tv-show/" in r[0]]

        return search_result if len(search_result) > 0 else None
    else:
        return None

def anime_search(query:str):

    search_gql = """
       query(
        $search: SearchInput
        $limit: Int
        $page: Int
        $translationType: VaildTranslationTypeEnumType
        $countryOrigin: VaildCountryOriginEnumType
       ) {
        shows(
            search: $search
            limit: $limit
            page: $page
            translationType: $translationType
            countryOrigin: $countryOrigin
        ) {
            edges {
                _id
                name
                availableEpisodes
                __typename
                thumbnail
            }
        }
       }
       """      
    variables = {
            "search": {
                "allowAdult": True,
                "allowUnknown": False,
                "query": query
            },
            "limit": 40,
            "page": 1,
            "translationType": "sub",
            "countryOrigin": "ALL"
       }

    payload = {
            "variables":json.dumps(variables),
            "query": search_gql

            }

    r = httpx.get(
                f"{ANIME_API}/api",
                headers={
                        "User-Agent" : USER_AGENT,
                        "Referer" : ANIME_REF
                    },
                params = payload
            )

    if r.status_code == 200:
        data = r.json()
        search_result = [(i["_id"],i["thumbnail"],i["name"]) for i in data["data"]["shows"]["edges"]]

        return search_result if len(search_result) > 0 else None
    else:
        return None




app = Flask(__name__)
app.config['SECRET_KEY'] = 'thiadgysgfwefbwhefweyfgwyefgwyegwuynsdcjsn'

@app.route('/')
def home():
    return render_template("index.html")

@app.route('/search', methods=['POST'])
def search():
    media_type = request.form.get('media_type')
    query = request.form.get('query')
    #return f"Media Type: {media_type}, Query: {query}"
    if media_type == "movie" or media_type == "tv":
        search_result = pop_search(media_type=media_type,query=query)
        if search_result:
            return render_template('result.html',results=search_result,media_type=media_type)
            
        else:
            return "<p>Sorry no data found</p>"
    else:
        search_result = anime_search(query=query)
        if search_result:
            return render_template('result.html',results=search_result,media_type=media_type)
        else:
            return "<p>No anime found</p>"

@app.route('/api/send_media')
def send_data():
    link = request.args.get('link')
    media_type = request.args.get('mediaType')
    media_name = request.args.get('media_name')
    if media_type == "movie":
        tmdb_id = get_tmdb(url=link)
        auto_url = f"{AUTO_CDN}/api/getVideoSource?type=movie&id={tmdb_id}"
        auto_headers = {"Referer": f"{AUTO_CDN}/movie/{tmdb_id}", "User-Agent" : USER_AGENT}

        streaming_link,subtitle = autoembed_scrapper(url=auto_url,headers=auto_headers)
        
        if not streaming_link:
            return "<p>Sorry no streaminng link available</p>"
        

        return render_template("movie.html",streaming_link=streaming_link,sub_url=subtitle,movie_name = media_name)

    elif media_type == "tv":
        tv_link = link.replace("/tv-show/","/episode/")
        tv_link += '/1-1'
        series_data = {"seasons":{}}

        tmdb_id = get_tmdb(url=tv_link)
        #gather episode data
        r = httpx.get(
                f"https://api.tmdb.org/3/tv/{tmdb_id}?append_to_response=external_ids",
                headers={
                    "Authorization": "Bearer eyJhbGciOiJIUzI1NiJ9.eyJhdWQiOiJmYWNkMmE1YWE0YmMwMzAyZjNhZmRlYTIwZGQ2YWRhZSIsInN1YiI6IjY1OTEyNjU1NjUxZmNmNWYxMzhlMWRjNyIsInNjb3BlcyI6WyJhcGlfcmVhZCJdLCJ2ZXJzaW9uIjoxfQ.5boG-w-nlk-SWB8hvFeWq_DNRbrU6n5XEXleVQ1L1Sg",
                    "User-Agent" : USER_AGENT
                    },
                timeout=None
                )

        seasons = r.json()["seasons"]
        for s in seasons:
            if s['season_number'] != 0:
                series_data['seasons'][s['season_number']] = list(range(1,int(s['episode_count']+1)))

        series_data["tmdb_id"] = tmdb_id
        return render_template("series.html",series_name=media_name,series_data=series_data)


    else:
        episode_list = anime_episode(link)

        #get streaming link of ep 1
        streaming_link = anime_scrapper(link,1) 
        #print(streaming_link)
        return render_template("anime.html",episodes=episode_list,anime_id=link,anime_name=media_name,streming_link=streaming_link)


@app.route('/api/get_streaming_link')
def get_tv_stream():
    tmdb_id = request.args.get('tmdb')
    season = request.args.get('season')
    episode = request.args.get('episode')
    
    #print("I got called")

    auto_url = f"{AUTO_CDN}/api/getVideoSource?type=tv&id={tmdb_id}/{season}/{episode}"
    auto_headers = {"Referer": f"{AUTO_CDN}/tv/{tmdb_id}/{season}/{episode}", "User-Agent" : USER_AGENT}

    streaming_link,sub = autoembed_scrapper(url=auto_url,headers=auto_headers)

    if not streaming_link:
        return "<p>Sorry no streaming link found for this series</p>"

    return jsonify({"streaming_link": streaming_link, "sub" : sub})



@app.route('/api/get_anime_stream_link')
def get_anime_stream():
    anime_id = request.args.get('id')
    ep = request.args.get('ep')

    streaming_link = anime_scrapper(anime_id,ep)
    #print(streaming_link)

    return jsonify({"streaming_link" : streaming_link})
