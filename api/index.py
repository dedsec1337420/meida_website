from flask import Flask, render_template_string
from test import return_int

app = Flask(__name__)

@app.route('/')
def home():
    return 'Hello, World!'

@app.route('/about')
def about():
    return 'About'

@app.route('/random_number')
def random_number():
    html = f'<p>{return_int()}</p>'
    return render_template_string(html)
