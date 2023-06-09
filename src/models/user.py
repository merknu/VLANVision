# Path: src\models\user.py
# Description: This is the class for user model
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from src.security.user import UserManager


# You need to provide the path to your user data file
user_manager = UserManager("user_data.json")


class User(UserMixin):
    def __init__(self, id, username, password):
        self.id = id
        self.username = username
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    @staticmethod
    def get(id):
        # Retrieve the user from the UserManager's users dictionary
        user = user_manager.users.get(id)

        if user:
            # Return a new User object with the same attributes as the retrieved user
            return User(id=user.username, username=user.username, password=user.password_hash)

        return None
