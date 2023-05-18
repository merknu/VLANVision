# Path: /src/security/user.py
# This is the class for user management system (login, logout, etc.)
import hashlib
import secrets
import json


class User:
    def __init__(self, username, password_hash, role, salt=None):
        self.username = username
        self.password_hash = password_hash
        self.role = role
        self.salt = salt or secrets.token_hex(16)

    def verify_password(self, password):
        password_hash = hashlib.pbkdf2_hmac(
            'sha256', password.encode('utf-8'), self.salt.encode('utf-8'), 100000
        ).hex()
        return self.password_hash == password_hash

    def to_dict(self):
        return {
            'username': self.username,
            'password_hash': self.password_hash,
            'role': self.role,
            'salt': self.salt
        }

    @staticmethod
    def from_dict(user_data):
        return User(
            user_data['username'],
            user_data['password_hash'],
            user_data['role'],
            user_data['salt']
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

        salt = secrets.token_hex(16)
        password_hash = hashlib.pbkdf2_hmac(
            'sha256', password.encode('utf-8'), salt.encode('utf-8'), 100000
        ).hex()
        user = User(username, password_hash, role, salt)
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
