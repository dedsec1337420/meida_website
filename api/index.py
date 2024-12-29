from flask import Flask, render_template
from flask import request
import httpx
import re

#global shit
USER_AGENT:str = 'Mozilla/5.0 (X11; Linux x86_64; rv:133.0) Gecko/20100101 Firefox/133.0'
POP_MAIN_URL:str ="https://popcornmovies.to"
ANIME_URL:str =""
ANIME_REF:str = ""



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
    pass


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


#if __name__ == '__main__':
#    app.run(host='0.0.0.0',port=8888,debug=True)

