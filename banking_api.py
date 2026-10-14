import os
import re

from dotenv import load_dotenv

# Load variables from the .env file
load_dotenv()

from account_service import AccountService
from flask import Flask, request
from flask_jwt_extended import JWTManager, create_access_token, get_jwt, get_jwt_identity, jwt_required
from loan_service import LoanService
from markupsafe import escape

app = Flask(__name__)
jwt_secret = os.environ.get("JWT_SECRET_KEY")
if not jwt_secret:
    raise ValueError("No JWT_SECRET_KEY set for Flask application. Please create a .env file.")

app.config["JWT_SECRET_KEY"] = jwt_secret
jwt = JWTManager(app)
account_service = AccountService()
loan_service = LoanService()


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
    if not _validate_username(username):
        return "\n------------------------------ \nInvalid. Username must have length 3-20 and be alphanumeric characters\n------------------------------\n"
    elif not _validate_password(password):
        return "\n------------------------------ \nInvalid. Password must have length 8-32 and only allows special characters: [@$!%*?&]\n------------------------------\n"

    # Verify user exists
    (user_id, role) = account_service.verify_user(username, password)

    # If user does not exist
    if user_id is None:
        return "\n------------------------------ \nUnauthorized: HTTP response 401\n------------------------------\n"

    access_token = create_access_token(identity=str(user_id), additional_claims={"role": role})

    return f'\n------------------------------ \nLogin in Progress \nAccess token: {access_token}\n \nUse your access token to access your account:\ncurl -X GET 127.0.0.1:5000/account -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \n------------------------------\n'


@app.route("/account", methods=["GET"])
@jwt_required()
def account():
    user_id = int(get_jwt_identity())
    balance = account_service.look_up_balance(user_id)
    username = account_service.get_username(user_id)

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

    user_id = int(get_jwt_identity())
    balance = account_service.look_up_balance(user_id)

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
        return "\n------------------------------ \nInvalid. Recipient ID and Amount to transfer must be integers\n------------------------------\n"

    amount_to_transfer = int(amount_to_transfer)

    # Check that the uses has enough funds to make the transfer possible
    if amount_to_transfer > balance:
        return "\n------------------------------ \nYou do not have enough money in your account to make this transfer possible\n------------------------------\n"

    # Make the transfer of funds
    account_service.transfer_funds(recipient_id, amount_to_transfer, user_id)

    # Get the new balance of the user
    new_balance = account_service.look_up_balance(user_id)

    return f"\n------------------------------ \nTransfer successful \n\nbalance: ${new_balance}\n------------------------------\n"


@app.route("/loan", methods=["POST"])
@jwt_required()
def loan():
    # Check that the user is not admin
    claims = get_jwt()
    if claims.get("role") == "admin":
        return "\n------------------------------ \nUnauthorized: Admins cannot use customer loan endpoint. Please use /admin\n------------------------------\n"

    user_id = int(get_jwt_identity())

    # Get the POST arguments
    loan_amount = request.form.get("amount")

    if not loan_amount:
        return "\n------------------------------ \nMissing loan amount\n------------------------------\n"

    # Sanitize the input
    loan_amount = _sanitize_input(loan_amount)

    # Validate the input
    if not _validate_id_or_amount(loan_amount):
        return "\n------------------------------ \nInvalid. Amount to transfer must be an integer\n------------------------------\n"

    loan_amount = int(loan_amount)

    # Call the loan service
    approve = loan_service.approve_loan(user_id, loan_amount)

    if not approve:
        return "\n------------------------------ \nLoan NOT approved \nThe wanted amount should be less than your balance\n------------------------------\n"

    # Loan has been approved, therefore add it to the user
    account_service.add_loan(user_id, loan_amount)

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
        return "\n------------------------------ \nInvalid. Sender ID, Recipient ID and Amount to transfer must be integers\n------------------------------\n"

    sender_id = int(sender_id)
    recipient_id = int(recipient_id)
    amount_to_transfer = int(amount_to_transfer)

    sender_username = account_service.get_username(sender_id)
    recipient_username = account_service.get_username(recipient_id)

    sender_balance_before = account_service.look_up_balance(sender_id)
    recipient_balance_before = account_service.look_up_balance(recipient_id)

    # Check that the users have enough balance on their accounts
    if amount_to_transfer > sender_balance_before:
        return f"\n------------------------------ \n{sender_username} Does not have enough money in their account to make this transfer possible\n------------------------------\n"

    account_service.transfer_funds(recipient_id, amount_to_transfer, sender_id)

    sender_balance_after = account_service.look_up_balance(sender_id)
    recipient_balance_after = account_service.look_up_balance(recipient_id)

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
        # Check if the amount can be parsed as an integer
        int(input)
        return True
    except ValueError:
        return False


if __name__ == "__main__":
    is_debug = os.environ.get("FLASK_DEBUG", "False").lower() == "true"
    app.run(debug=is_debug)
