import os
import re

import requests
from dotenv import load_dotenv

# Load variables from the .env file
load_dotenv()

from flask import Flask, request
from flask_jwt_extended import JWTManager, create_access_token, get_jwt, get_jwt_identity, jwt_required
from markupsafe import escape

app = Flask(__name__)
jwt_secret = os.environ.get("JWT_SECRET_KEY")
if not jwt_secret:
    raise ValueError("No JWT_SECRET_KEY set for Flask application. Please create a .env file.")

app.config["JWT_SECRET_KEY"] = jwt_secret
jwt = JWTManager(app)

# The URL for the Account Service & the Loan Service
ACCOUNT_SERVICE_URL = "http://127.0.0.1:5001"
LOAN_SERVICE_URL = "http://127.0.0.1:5002"


@app.route("/", methods=["GET"])
def front_page():
    if request.method == "GET":
        return "\n------------------------------ \nWelcome to the Banking API. You can log in at /login\ncurl -X GET 127.0.0.1:5000/login\n------------------------------\n"
    else:
        return f"\n------------------------------ \nInvalid HTTP request {request.method} \n------------------------------ \n"


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "GET":
        return '\n------------------------------ \nWelcome to the login page.\nPlease provide your username and password in this format:\n\ncurl -X POST 127.0.0.1:5000/login -d username=YOUR_USERNAME --data-urlencode password="YOUR_PASSWORD" \n------------------------------\n'

    username = request.form.get("username")
    password = request.form.get("password")

    if not username or not password:
        return "\n------------------------------ \nMissing username or password\n------------------------------\n"

    # Sanitize the input (not password)
    username = _sanitize_input(username)

    # Validate the input
    if not _validate_username(username) or not _validate_password(password):
        return "\n------------------------------ \nInvalid Username or Password\n------------------------------\n"
    
    # Verify user exists
    response = requests.post(f"{ACCOUNT_SERVICE_URL}/verify", json={"username": username, "password": password}, timeout=5)
    data = response.json()
    user_id = data.get("user_id")
    role = data.get("role")

    # If user does not exist
    if user_id is None:
        return "\n------------------------------ \nUnauthorized: HTTP response 401\n------------------------------\n"

    access_token = create_access_token(identity=str(user_id), additional_claims={"role": role})

    return f'\n------------------------------ \nLogin in Progress \nAccess token: {access_token}\n \nUse your access token to access your account:\ncurl -X GET 127.0.0.1:5000/account -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \n------------------------------\n'


@app.route("/account", methods=["GET"])
@jwt_required()
def account():
    user_id = int(get_jwt_identity())

    # Extract the JWT token
    auth_header = {"Authorization": request.headers.get("Authorization")}

    # Get balance and username
    balance_response = requests.get(f"{ACCOUNT_SERVICE_URL}/balance/{user_id}", headers=auth_header, timeout=5)
    balance = balance_response.json().get("balance")
    username_response = requests.get(f"{ACCOUNT_SERVICE_URL}/username/{user_id}", headers=auth_header, timeout=5)
    username = username_response.json().get("username")

    # Check that the user is admin or user
    claims = get_jwt()
    if claims.get("role") == "admin":
        return f'\n------------------------------\nLogin Sucessfull. Welcome {username} \n\nAdmins can go to \ncurl -X GET 127.0.0.1:5000/admin -H "Authorization: Bearer YOUR_ACCESS_TOKEN"\n------------------------------\n'

    elif claims.get("role") == "user":
        return f'\n------------------------------\nLogin Sucessfull. Welcome {username} \nBalance: ${balance} \n\nYou are able to transfer funds to another user by providing their ID and the amount \ncurl -X POST 127.0.0.1:5000/transfer -H "Authorization: Bearer YOUR_ACCESS_TOKEN" -d id=RECEIVER_ID -d amount=DESIRED_AMOUNT_TO_SEND \n\nYou can apply for a loan by specifying the amount you need \ncurl -X POST 127.0.0.1:5000/loan -H "Authorization: Bearer YOUR_ACCESS_TOKEN" -d amount=DESIRED_AMOUNT_TO_LOAN\n------------------------------\n'


@app.route("/transfer", methods=["POST"])
@jwt_required()
def transfer():
    # Check that the user is not admin
    claims = get_jwt()
    if claims.get("role") == "admin":
        return "\n------------------------------ \nUnauthorized: Admins cannot use customer transfer endpoint. Please use /admin\n------------------------------\n"

    # Extract the JWT token
    auth_header = {"Authorization": request.headers.get("Authorization")}

    user_id = int(get_jwt_identity())
    balance_response = requests.get(f"{ACCOUNT_SERVICE_URL}/balance/{user_id}", headers=auth_header, timeout=5)
    balance = balance_response.json().get("balance")

    # Get the POST arguments
    recipient_id = request.form.get("id")
    amount_to_transfer = request.form.get("amount")

    if not recipient_id or not amount_to_transfer:
        return "\n------------------------------ \nMissing recipient ID or amount to transfer\n------------------------------\n"

    # Sanitize the input
    recipient_id = _sanitize_input(recipient_id)
    amount_to_transfer = _sanitize_input(amount_to_transfer)

    # Validate the input
    if not _validate_id_or_amount(recipient_id) or not _validate_id_or_amount(amount_to_transfer):
        return "\n------------------------------ \nInvalid. Recipient ID and Amount to transfer must be integers and greater than 0\n------------------------------\n"

    amount_to_transfer = int(amount_to_transfer)

    # Check that the uses has enough funds to make the transfer possible
    if amount_to_transfer > balance:
        return "\n------------------------------ \nYou do not have enough money in your account to make this transfer possible\n------------------------------\n"

    # Make the transfer of funds
    requests.post(f"{ACCOUNT_SERVICE_URL}/transfer", json={"recipient_id": recipient_id, "amount": amount_to_transfer, "user_id": user_id}, headers=auth_header, timeout=5)

    # Get the new balance of the user
    new_balance_response = requests.get(f"{ACCOUNT_SERVICE_URL}/balance/{user_id}", headers=auth_header, timeout=5)
    new_balance = new_balance_response.json().get("balance")

    return f"\n------------------------------ \nTransfer successful \n\nbalance: ${new_balance}\n------------------------------\n"


@app.route("/loan", methods=["POST"])
@jwt_required()
def loan():
    # Check that the user is not admin
    claims = get_jwt()
    if claims.get("role") == "admin":
        return "\n------------------------------ \nUnauthorized: Admins cannot use customer loan endpoint. Please use /admin\n------------------------------\n"

    user_id = int(get_jwt_identity())

    # Extract the JWT token
    auth_header = {"Authorization": request.headers.get("Authorization")}

    # Get the POST arguments
    loan_amount = request.form.get("amount")

    if not loan_amount:
        return "\n------------------------------ \nMissing loan amount\n------------------------------\n"

    # Sanitize the input
    loan_amount = _sanitize_input(loan_amount)

    # Validate the input
    if not _validate_id_or_amount(loan_amount):
        return "\n------------------------------ \nInvalid. Amount to transfer must be an integer and greater than 0\n------------------------------\n"

    loan_amount = int(loan_amount)

    # Call the loan service
    loan_response = requests.post(f"{LOAN_SERVICE_URL}/approve", json={"user_id": user_id, "loan_amount": loan_amount}, headers=auth_header, timeout=5)
    approve = loan_response.json().get("approved")

    if not approve:
        return "\n------------------------------ \nLoan NOT approved \nThe wanted amount should be less than your balance\n------------------------------\n"

    # Loan has been approved, therefore add it to the user
    requests.post(f"{ACCOUNT_SERVICE_URL}/loan", json={"user_id": user_id, "loan_amount": loan_amount}, headers=auth_header, timeout=5)

    return f"\n------------------------------ \nLoan of ${loan_amount} has been added to your account. Only one loan per user is possible\n------------------------------\n"


@app.route("/admin", methods=["GET", "POST"])
@jwt_required()
def admin():
    # Check that the user is admin
    claims = get_jwt()
    if claims.get("role") != "admin":
        return "\n------------------------------ \nUnauthorized: HTTP response 401\n------------------------------\n"

    if request.method == "GET":
        return '\n------------------------------ \nHello Admin \n\nHere you can transfer money between accounts. To do this please provide the sender ID, recipient ID and the amount \n\ncurl -X POST 127.0.0.1:5000/admin -H "Authorization: Bearer YOUR_ACCESS_TOKEN" -d sender_id=SENDER_ID -d recipient_id=RECIPIENT_ID -d amount=DESIRED_AMOUNT_TO_SEND"\n------------------------------\n'

    # Extract the JWT token
    auth_header = {"Authorization": request.headers.get("Authorization")}

    sender_id = request.form.get("sender_id")
    recipient_id = request.form.get("recipient_id")
    amount_to_transfer = request.form.get("amount")

    if not sender_id or not recipient_id or not amount_to_transfer:
        return "\n------------------------------ \nMissing sender ID or recipient ID or amount to transfer\n------------------------------\n"

    # Sanitize the input
    sender_id = _sanitize_input(sender_id)
    recipient_id = _sanitize_input(recipient_id)
    amount_to_transfer = _sanitize_input(amount_to_transfer)

    # Validate the input
    if not _validate_id_or_amount(sender_id) or not _validate_id_or_amount(recipient_id) or not _validate_id_or_amount(amount_to_transfer):
        return "\n------------------------------ \nInvalid. Sender ID, Recipient ID and Amount to transfer must be integers and greater than 0\n------------------------------\n"

    sender_id = int(sender_id)
    recipient_id = int(recipient_id)
    amount_to_transfer = int(amount_to_transfer)

    sender_username_response = requests.get(f"{ACCOUNT_SERVICE_URL}/username/{sender_id}", headers=auth_header, timeout=5)
    sender_username = sender_username_response.json().get("username")

    recipient_username_response = requests.get(f"{ACCOUNT_SERVICE_URL}/username/{recipient_id}", headers=auth_header, timeout=5)
    recipient_username = recipient_username_response.json().get("username")

    sender_balance_before_response = requests.get(f"{ACCOUNT_SERVICE_URL}/balance/{sender_id}", headers=auth_header, timeout=5)
    sender_balance_before = sender_balance_before_response.json().get("balance")

    recipient_balance_before_response = requests.get(f"{ACCOUNT_SERVICE_URL}/balance/{recipient_id}", headers=auth_header, timeout=5)
    recipient_balance_before = recipient_balance_before_response.json().get("balance")

    # Check that the users have enough balance on their accounts
    if amount_to_transfer > sender_balance_before:
        return f"\n------------------------------ \n{sender_username} Does not have enough money in their account to make this transfer possible\n------------------------------\n"

    requests.post(f"{ACCOUNT_SERVICE_URL}/transfer", json={"recipient_id": recipient_id, "amount": amount_to_transfer, "user_id": sender_id}, headers=auth_header, timeout=5)

    sender_balance_after_response = requests.get(f"{ACCOUNT_SERVICE_URL}/balance/{sender_id}", headers=auth_header, timeout=5)
    sender_balance_after = sender_balance_after_response.json().get("balance")

    recipient_balance_after_response = requests.get(f"{ACCOUNT_SERVICE_URL}/balance/{recipient_id}", headers=auth_header, timeout=5)
    recipient_balance_after = recipient_balance_after_response.json().get("balance")

    return f"\n------------------------------ \nTransfer successful \n\n{sender_username}: {sender_balance_before} -> {sender_balance_after} \n{recipient_username}: {recipient_balance_before} -> {recipient_balance_after}\n------------------------------\n"


def _sanitize_input(input: str) -> str:
    # remove whitespace
    clean_input = input.strip()

    # Escape HTML tags (to prevent XSS)
    clean_input = escape(clean_input)

    return clean_input


def _validate_username(username: str) -> bool:
    # Usernames: 3-20 alphanumeric characters
    return bool(re.match(r"^[a-zA-Z0-9]{3,20}$", username))


def _validate_password(password: str) -> bool:
    # Passwords: 8-32 chars, requires at least 1 lowercase, 1 uppercase, 1 number, and 1 special char
    return bool(re.match(r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]{8,32}$", password))


def _validate_id_or_amount(input: str) -> bool:
    try:
        # Check if the input can be parsed as an integer and is higher than 0
        value = int(input)
        return value > 0
    except ValueError:
        return False


if __name__ == "__main__":
    is_debug = os.environ.get("FLASK_DEBUG", "False").lower() == "true"
    app.run(debug=is_debug)
