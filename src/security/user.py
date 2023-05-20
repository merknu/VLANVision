# Path: /src/security/user.py
# This is the class for user management system (login, logout, etc.)
from werkzeug.security import generate_password_hash, check_password_hash
import json


class User:
    def __init__(self, username, password, role):
        self.username = username
        self.password_hash = generate_password_hash(password)
        self.role = role

    def verify_password(self, password):
        return check_password_hash(self.password_hash, password)

    def to_dict(self):
        return {
            'username': self.username,
            'password_hash': self.password_hash,
            'role': self.role,
        }

    @staticmethod
    def from_dict(user_data):
        return User(
            user_data['username'],
            user_data['password_hash'],
            user_data['role'],
        )


class UserManager:
    def __init__(self, user_data_file):
        self.user_data_file = user_data_file
        self.users = self.load_users()

    def load_users(self):
        try:
            with open(self.user_data_file, 'r') as file:
                user_data = json.load(file)
        except FileNotFoundError:
            user_data = []

        users = {}
        for user_dict in user_data:
            user = User.from_dict(user_dict)
            users[user.username] = user

        return users

    def save_users(self):
        user_data = [user.to_dict() for user in self.users.values()]
        with open(self.user_data_file, 'w') as file:
            json.dump(user_data, file, indent=2)

    def add_user(self, username, password, role):
        if username in self.users:
            raise ValueError("User already exists.")
        user = User(username, password, role)
        self.users[username] = user
        self.save_users()

    def remove_user(self, username):
        if username not in self.users:
            raise ValueError("User not found.")
        del self.users[username]
        self.save_users()

    def authenticate(self, username, password):
        user = self.users.get(username)
        if user and user.verify_password(password):
            return user.role
        return None
