from account_service import AccountService
from loan_helper import evaluate_loan


class LoanService:
    def __init__(self):
        self.account_service = AccountService()

    def get_user_balance(self, user_id: int):
        return self.account_service.look_up_balance(user_id)

    def approve_loan(self, user_id: int, loan_amount: int):
        user_balance = self.get_user_balance(user_id)

        # Call external library
        return evaluate_loan(user_balance, loan_amount)
