import os
import sqlite3
from pathlib import Path

import bcrypt
from dotenv import load_dotenv
from flask import Flask, jsonify, request
from flask_jwt_extended import JWTManager, jwt_required

load_dotenv()

app = Flask(__name__)
jwt_secret = os.environ.get("JWT_SECRET_KEY")
if not jwt_secret:
    raise ValueError("No JWT_SECRET_KEY set for Flask application. Please create a .env file.")

app.config["JWT_SECRET_KEY"] = jwt_secret
jwt = JWTManager(app)


class AccountService:
    def __init__(self):
        self.database_path = Path(__file__).parent / "database.db"

    def _compare_passwords(self, given_password: str, hashed_password) -> str:
        given_password = given_password.encode("utf-8")
        hashed_password = hashed_password.encode("utf-8")

        return bcrypt.checkpw(given_password, hashed_password)

    def get_username(self, user_id: int) -> str:
        sqlite_connection = sqlite3.connect(self.database_path)
        cursor = sqlite_connection.cursor()
        query = "SELECT username FROM Accounts WHERE ID = ?"
        cursor.execute(query, (user_id,))

        username = cursor.fetchall()
        sqlite_connection.close()

        return username[0][0]

    def verify_user(self, username: str, password: str) -> tuple[int, str] | tuple[None, None]:
        sqlite_connection = sqlite3.connect(self.database_path)
        cursor = sqlite_connection.cursor()
        query = "SELECT ID, role, password FROM Accounts WHERE username = ?"
        cursor.execute(query, (username,))

        result = cursor.fetchone()
        sqlite_connection.close()

        # Check if username exists otherwise return none
        if result is None:
            return (None, None)

        # unpack result because username exists
        user_id, role, password_hash = result

        # Check if passwords match
        if self._compare_passwords(password, password_hash):
            return (user_id, role)

        # Passwords does not match
        else:
            return (None, None)

    def look_up_balance(self, user_id: int) -> int:
        sqlite_connection = sqlite3.connect(self.database_path)
        cursor = sqlite_connection.cursor()
        query = "SELECT balance FROM Accounts WHERE ID = ?"
        cursor.execute(query, (user_id,))

        balance = cursor.fetchone()

        sqlite_connection.close()

        return balance[0]

    def transfer_funds(self, recipent_id: int, amount: int, user_id: int):
        sqlite_connection = sqlite3.connect(self.database_path)
        cursor = sqlite_connection.cursor()
        query_subtract_amount_from_sender = "UPDATE Accounts SET balance = balance - ? WHERE ID = ?"
        cursor.execute(query_subtract_amount_from_sender, (amount, user_id))

        query_add_amount_to_receiver = "UPDATE Accounts SET balance = balance + ? WHERE ID = ?"
        cursor.execute(query_add_amount_to_receiver, (amount, recipent_id))

        sqlite_connection.commit()
        sqlite_connection.close()

    def add_loan(self, user_id: int, loan_amount: int):
        sqlite_connection = sqlite3.connect(self.database_path)
        cursor = sqlite_connection.cursor()
        query_add_loan_amount = "UPDATE Accounts SET balance = balance + ? WHERE ID = ?"
        cursor.execute(query_add_loan_amount, (loan_amount, user_id))

        query_record_the_user_has_a_loan = "UPDATE Accounts SET has_loan = true WHERE ID = ?"
        cursor.execute(query_record_the_user_has_a_loan, (user_id,))

        sqlite_connection.commit()
        sqlite_connection.close()


service = AccountService()


# HTTP Endpoints for the Account Service
@app.route("/username/<int:user_id>", methods=["GET"])
@jwt_required()
def get_username(user_id):
    username = service.get_username(user_id)
    return jsonify({"username": username})


@app.route("/verify", methods=["POST"])
def verify_user():
    data = request.json
    user_id, role = service.verify_user(data["username"], data["password"])
    return jsonify({"user_id": user_id, "role": role})


@app.route("/balance/<int:user_id>", methods=["GET"])
@jwt_required()
def look_up_balance(user_id):
    balance = service.look_up_balance(user_id)
    return jsonify({"balance": balance})


@app.route("/transfer", methods=["POST"])
@jwt_required()
def transfer_funds():
    data = request.json
    service.transfer_funds(data["recipient_id"], data["amount"], data["user_id"])
    return jsonify({"status": "success"})


@app.route("/loan", methods=["POST"])
@jwt_required()
def add_loan():
    data = request.json
    service.add_loan(data["user_id"], data["loan_amount"])
    return jsonify({"status": "success"})


if __name__ == "__main__":
    # Run the Account Service on port 5001
    is_debug = os.environ.get("FLASK_DEBUG", "False").lower() == "true"
    app.run(port=5001, debug=is_debug)
