# Path: src\models\user.py
# Description: This is the class for user model
from flask_login import UserMixin
from src.security.user import UserManager
from werkzeug.security import generate_password_hash, check_password_hash, gen_salt


# You need to provide the path to your user data file
user_manager = UserManager("user_data.json")


class User(UserMixin):
    def __init__(self, user_id, username, password, salt=None):
        self.id = user_id
        self.username = username
        self.salt = gen_salt(12) if not salt else salt  # gen_salt function requires a length argument
        self.password_hash = generate_password_hash(password + self.salt)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password + self.salt)

    @staticmethod
    def get(user_id):
        # Retrieve the user from the UserManager's users dictionary
        user = user_manager.users.get(user_id)

        if user:
            # Return a new User object with the same attributes as the retrieved user
            return User(user_id=user.username, username=user.username, password=user.password_hash)

        return None
