from flask import Flask, render_template
from flask import request
from flask import jsonify
import httpx
import re
import json
from base64 import b64decode
from base64 import b64encode
from Cryptodome.Cipher import AES

#global shit
USER_AGENT:str = 'Mozilla/5.0 (X11; Linux x86_64; rv:133.0) Gecko/20100101 Firefox/133.0'

POP_MAIN_URL:str ="https://popcornmovies.to"
ANIME_URL:str ="https://allanime.day"
ANIME_REF:str = "https://allmanga.to"
ANIME_API:str = "https://api.allanime.day"
AUTO_EMBED:str = "https://tom.autoembed.cc"


#streaming stuff


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
    s=b'37911490979715163134003223491201'
    s_2 = b'54674138327930866480207815084989'
    iv= b'3134003223491201'
    

    def pad(data):
        return data + chr(len(data) %16)*(16 - len(data) %16)

    def decrypt(key,data):
        return AES.new(key,AES.MODE_CBC,iv=iv).decrypt(b64decode(data))

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
        host,slug  = re.findall(r'"sourceUrl":"https://(.*?)/streaming\.php\?(id=.*?)"',r.text)[0]
        r = httpx.get(
                    f"https://{host}/streaming.php?{slug}",
                    headers={
                        "User-Agent" : USER_AGENT

                        },
                    timeout=None
                )
        #extract crypto value
        crypto_value = re.findall(r'data-value="(.*?)"',r.text)[0]

        decrypted_crypto_value = decrypt(s,crypto_value).strip(b"\x00\x01\x02\x03\x04\x05\x06\x07\x08\t\n\x0b\x0c\r\x0e\x0f\x10").decode()
        #print(decrypted_crypto_value)
        media_id = decrypted_crypto_value.split('&')[0]
        media_slug = decrypted_crypto_value[len(media_id):]

        encrypted_media_id = b64encode(
                AES.new(s,AES.MODE_CBC,iv=iv).encrypt(
                    pad(media_id).encode()
                    )

                ) 

        r = httpx.get(
                    f"https://{host}/encrypt-ajax.php?id={encrypted_media_id.decode()}{media_slug}&alias={media_id}",
                    headers={
                        "User-Agent" : USER_AGENT,
                        "X-Requested-With": "XMLHttpRequest"
                        },
                    timeout=None
                )
        j = json.loads(
                decrypt(s_2,r.json().get("data")).strip(b"\x00\x01\x02\x03\x04\x05\x06\x07\x08\t\n\x0b\x0c\r\x0e\x0f\x10")
                )

        return j['source'][0]['file']



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
        pass
    elif media_type == "tv":
        pass
    else:
        episode_list = anime_episode(link)

        #get streaming link of ep 1
        streaming_link = anime_scrapper(link,1) 
        #print(streaming_link)
        return render_template("anime.html",episodes=episode_list,anime_id=link,anime_name=media_name,streming_link=streaming_link)


@app.route('/api/get_anime_stream_link')
def get_anime_stream():
    anime_id = request.args.get('id')
    ep = request.args.get('ep')

    streaming_link = anime_scrapper(anime_id,ep)
    #print(streaming_link)

    return jsonify({"streaming_link" : streaming_link})


#if __name__ == '__main__':
#    app.run(host='0.0.0.0',port=8888,debug=True)
#
