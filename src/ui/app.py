# Path: src/ui/app.py
# Description: This is the main entry point for the UI application
from flask import Flask, render_template

app = Flask(__name__, template_folder='../ui')


@app.route('/')
def index():
    return render_template('index.html')


def run():
    app.run(debug=True)
