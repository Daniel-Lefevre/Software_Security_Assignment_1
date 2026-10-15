import os

import requests
from flask import Flask, jsonify, request
from loan_helper import evaluate_loan

app = Flask(__name__)
ACCOUNT_SERVICE_URL = "http://127.0.0.1:5001"


@app.route("/approve", methods=["POST"])
def approve_loan():
    data = request.json
    user_id = data["user_id"]
    loan_amount = data["loan_amount"]

    balance_resp = requests.get(f"{ACCOUNT_SERVICE_URL}/balance/{user_id}")
    user_balance = balance_resp.json().get("balance")

    # Call external library
    approved = evaluate_loan(user_balance, loan_amount)

    return jsonify({"approved": approved})


if __name__ == "__main__":
    is_debug = os.environ.get("FLASK_DEBUG", "False").lower() == "true"
    app.run(port=5002, debug=is_debug)
