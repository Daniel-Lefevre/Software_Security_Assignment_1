import os

import requests
from dotenv import load_dotenv
from flask import Flask, jsonify, request
from flask_jwt_extended import JWTManager, jwt_required
from loan_helper import evaluate_loan

load_dotenv()

app = Flask(__name__)
jwt_secret = os.environ.get("JWT_SECRET_KEY")
if not jwt_secret:
    raise ValueError("No JWT_SECRET_KEY set for Flask application. Please create a .env file.")

app.config["JWT_SECRET_KEY"] = jwt_secret
jwt = JWTManager(app)

ACCOUNT_SERVICE_URL = "http://127.0.0.1:5001"


@app.route("/approve", methods=["POST"])
@jwt_required()
def approve_loan():
    data = request.json
    user_id = data["user_id"]
    loan_amount = data["loan_amount"]

    # Extract the token
    auth_header = {"Authorization": request.headers.get("Authorization")}

    # Get the user's balance
    balance_response = requests.get(f"{ACCOUNT_SERVICE_URL}/balance/{user_id}", headers=auth_header, timeout=5)
    user_balance = balance_response.json().get("balance")

    # Call external library
    approved = evaluate_loan(user_balance, loan_amount)

    return jsonify({"approved": approved})


if __name__ == "__main__":
    is_debug = os.environ.get("FLASK_DEBUG", "False").lower() == "true"
    app.run(port=5002, debug=is_debug)
