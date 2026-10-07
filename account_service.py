import sqlite3
from pathlib import Path


class AccountService:
    def __init__(self):
        self.database_path = Path(__file__).parent / "database.db"

    def get_username(self, user_id: int):
        sqlite_connection = sqlite3.connect(self.database_path)
        cursor = sqlite_connection.cursor()
        query = "SELECT username FROM Accounts WHERE ID = ?"
        cursor.execute(query, (user_id,))

        username = cursor.fetchall()
        sqlite_connection.close()

        return username[0][0]

    def verify_user(self, username: str, password: str):
        sqlite_connection = sqlite3.connect(self.database_path)
        cursor = sqlite_connection.cursor()
        query = "SELECT ID, role FROM Accounts WHERE username = ? AND password = ?"
        cursor.execute(query, (username, password))

        user_id, role = cursor.fetchone()

        sqlite_connection.close()

        # If the user does not exist
        if user_id is None:
            return None

        return (user_id, role)

    def look_up_balance(self, user_id: int):
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
