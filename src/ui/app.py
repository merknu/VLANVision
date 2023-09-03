# Path: src/ui/app.py
# Description: This is the main entry point for the UI application. It is responsible for setting up
# the web server, defining the routes (the URLs that the app can respond to), and handling incoming HTTP requests.
from flask import Flask, render_template, request, jsonify, abort
from flask_login import LoginManager

# Assuming the User class is defined in a module named 'models'
from src.models.user import User
from src.network.vlan import VLANManager

app = Flask(__name__, template_folder='../ui')
login_manager = LoginManager(app)

# Instantiate VLANManager
vlan_manager = VLANManager()


@login_manager.user_loader
def load_user(user_id):
    return User.get(user_id)


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/dashboard')
def dashboard():
    return render_template('dashboard.html')


@app.route('/network')
def network():
    return render_template('network.html')


@app.route('/security')
def security():
    return render_template('security.html')


@app.route('/integration')
def integration():
    return render_template('integration.html')


@app.route('/help')
def help():
    return render_template('help.html')


@app.route('/api/data', methods=['GET'])
def api_data():
    return jsonify({"message": "ok"})


@app.route('/api/vlan', methods=['POST'])
def create_vlan():
    if not {'vlan_id', 'name', 'description'} <= request.json.keys():
        abort(400, description="Missing parameters")
    try:
        vlan_manager.create_vlan(request.json['vlan_id'], request.json['name'], request.json['description'])
        return jsonify({"message": "VLAN created successfully"}), 200
    except ValueError as e:
        abort(400, description=f"Failed to create VLAN. Reason: {str(e)}")


@app.route('/api/vlan/<int:vlan_id>', methods=['PUT'])
def update_vlan(vlan_id):
    if not {'name', 'description'} <= request.json.keys():
        abort(400, description="Missing parameters")
    try:
        vlan_manager.update_vlan(vlan_id, request.json['name'], request.json['description'])
        return jsonify({"message": "VLAN updated successfully"}), 200
    except ValueError as e:
        abort(400, description=f"Failed to update VLAN. Reason: {str(e)}")


@app.route('/api/vlan/<int:vlan_id>', methods=['DELETE'])
def delete_vlan(vlan_id):
    try:
        vlan_manager.delete_vlan(vlan_id)
        return jsonify({"message": "VLAN deleted successfully"}), 200
    except ValueError as e:
        abort(400, description=f"Failed to delete VLAN. Reason: {str(e)}")


@app.route('/api/vlan', methods=['GET'])
def list_vlans():
    vlans = vlan_manager.list_vlans()
    return jsonify({"vlans": vlans}), 200


@app.errorhandler(400)
def handle_bad_request(e):
    return jsonify({"error": str(e)}), 400


@app.errorhandler(500)
def handle_internal_error(e):
    return jsonify({"error": "Internal Server Error"}), 500


def run():
    app.run(debug=True, host='  127.0.0.1', port=5000)
    # Run the app in debug mode
