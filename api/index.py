from flask import Flask, render_template
import httpx
import re


client = httpx.Client(headers={'User-Agent':'Mozilla/5.0 (X11; Linux x86_64; rv:133.0) Gecko/20100101 Firefox/133.0'})

app = Flask(__name__)

@app.route('/')
def home():
    return 'Hello, World!'

@app.route('/about')
def about():
    return 'About'

@app.route('/random_number')
def random_number():
    r = client.get("https://popcornmovies.to/search/mr. robot")
    data = re.findall(r'<a href="(.*?)"\s+class=".*?">\s+<picture>\s+<img src=".*?" data-src="(.*?)"',r.text)[0]

    return render_template('index.html',url=data[0],image=data[1])


