import os
from datetime import datetime

import requests


class TransactionService:
    def __init__(self):
        self.base_url = 'https://192.168.30.78:8098'
        self.last_id_file = 'last_transaction_id.txt'

    def get_transactions(self, params):
        data = {
            'list': params.get('list', ''),
            'pageSize': params.get('pageSize', '50'),
            'beginDate': params.get('beginDate', '2025-04-01 00:00:00'),
            'endDate': params.get('endDate', '2025-04-21 23:59:59'),
            'limitCount': params.get('limitCount', '100000'),
            'pageList': params.get('pageList', 'true')
        }

        headers = {
            'Cookie': 'SESSION=OGE1YTc3OGItNDI0NC00YjIxLWE3NDYtZjI3YWM2Mzg5NzNh'
        }

        response = requests.post(
            f'{self.base_url}/attTransaction.do',
            data=data,
            headers=headers,
            verify=False
        )

        return response.json()

    def load_last_id(self):
        if not os.path.exists(self.last_id_file):
            return None
        with open(self.last_id_file, 'r') as file:
            return file.read().strip()

    def save_last_id(self, transaction_id):
        with open(self.last_id_file, 'w') as file:
            file.write(str(transaction_id))

    def process_new_transactions(self, transactions):
        rows = transactions.get("rows", [])
        if not rows:
            print("No transactions found.")
            return

        latest_id = rows[0].get("id")
        last_saved_id = self.load_last_id()

        if str(latest_id) == str(last_saved_id):
            print("No new transactions.")
            return

        result = []
        for row in transactions.get("rows", []):
            if row["id"] == last_saved_id:
                break
            result.append(row)

        self.save_last_id(latest_id)
        print(result)


if __name__ == "__main__":
    service = TransactionService()
    start_time = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    end_time = datetime.now().replace(hour=23, minute=59, second=59, microsecond=0)
    print(
        f"Getting transactions between {start_time.strftime('%Y-%m-%d %H:%M:%S')} and {end_time.strftime('%Y-%m-%d %H:%M:%S')}"
    )

    params = {
        'list': 'true',
        'pageSize': '50',
        'beginDate': start_time.strftime("%Y-%m-%d %H:%M:%S"),
        'endDate': end_time.strftime("%Y-%m-%d %H:%M:%S"),
        'limitCount': '100000',
        'pageList': 'true'
    }

    transactions = service.get_transactions(params)
    service.process_new_transactions(transactions)
