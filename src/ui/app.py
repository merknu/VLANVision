# Path: src/ui/app.py
# Description: This is the main entry point for the UI application. It is responsible for setting up
# the web server, defining the routes (the URLs that the app can respond to), and handling incoming HTTP requests.

from flask import Flask, render_template, request, jsonify
from flask_login import LoginManager

# Assuming the User class is defined in a module named 'models'
from src.models.user import User

app = Flask(__name__, template_folder='../ui')
login_manager = LoginManager(app)


@login_manager.user_loader
def load_user(user_id):
    """
    This callback is used to reload the user object from the user ID stored in the session.
    It should take the unicode ID of a user, and return the corresponding user object.
    """
    return User.get(user_id)


@app.route('/')
def index():
    """
    This is the home page route. When a user navigates to the root of your website (http://yourwebsite.com/),
    Flask will trigger this function and return the 'index.html' template.
    """
    return render_template('index.html')


@app.route('/dashboard')
def dashboard():
    """
    This is the dashboard route. This page could display statistics and other overview information
    about the user's network. This route would require loading any necessary data for the dashboard
    from the database or other sources.
    """
    return render_template('dashboard.html')


@app.route('/network')
def network():
    """
    This is the network route. This page could display network-specific information,
    such as a list of devices, a network topology diagram, etc. This route would require loading
    any necessary data for the network view from the database or other sources.
    """
    return render_template('network.html')


@app.route('/settings')
def settings():
    """
    This is the settings route. This page could allow the user to update their settings,
    such as changing their password, adjusting preferences, or managing API keys.
    """
    return render_template('settings.html')


@app.route('/api/data', methods=['GET', 'POST'])
def api_data():
    """
    This route handles API requests for data. Depending on the method of the request, it can either
    retrieve data (GET request) or update data (POST request).
    """
    if request.method == 'POST':
        # handle post request
        # This could involve updating a user's data based on the contents of the request
        pass
    else:
        # handle get request
        # This could involve retrieving data based on the request, such as returning a user's data
        pass
    return jsonify({"message": "ok"})


def run():
    """
    This function starts the Flask application's server.
    """
    app.run(debug=True)
