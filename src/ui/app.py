# Path: src/ui/app.py
# Description: This is the main entry point for the UI application
from flask import Flask, render_template, request, jsonify
from flask_login import LoginManager, current_user
# Assuming the User class is defined in a module named 'models'
from models import User

app = Flask(__name__, template_folder='../ui')
login_manager = LoginManager(app)


@login_manager.user_loader
def load_user(user_id):
    # This should return a user object if the user is authenticated, or None otherwise
    return User.get(user_id)


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/dashboard')
def dashboard():
    # load data required for dashboard
    return render_template('dashboard.html')


@app.route('/network')
def network():
    # load data related to network
    return render_template('network.html')


@app.route('/api/data', methods=['GET', 'POST'])
def api_data():
    if request.method == 'POST':
        # handle post request
        pass
    else:
        # handle get request
        pass
    return jsonify({"message": "ok"})


def run():
    app.run(debug=True)

