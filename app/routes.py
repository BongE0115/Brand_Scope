from flask import render_template
from app import app

@application.route('/')
@application.route('/index')
def index():
    return render_template('index.html', title='Home')