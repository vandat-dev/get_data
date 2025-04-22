import os
import time
from datetime import datetime, timedelta

import requests
import schedule
import urllib3
from requests.cookies import create_cookie

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class TransactionService:
    def __init__(self, session_token=None):
        self.base_url = 'https://192.168.30.78:8098'
        self.last_id_file = 'last_user_id.txt'
        self.session = requests.Session()
        self.session.verify = False
        if session_token:
            self.set_cookie(session_token)

    def set_cookie(self, token):
        """
        Manually add a SESSION cookie with a long expiry.
        """
        cookie = create_cookie(
            name='SESSION',
            value=token,
            domain='192.168.30.78',
            path='/',
            secure=True,
            expires=int((datetime.now() + timedelta(days=365)).timestamp()),
            rest={'HttpOnly': True, 'SameSite': 'Lax'}
        )
        self.session.cookies.set_cookie(cookie)

    def get_transactions(self, params):
        url = f"{self.base_url}/attTransaction.do"
        response = self.session.post(url, data=params)
        try:
            return response.json()
        except ValueError:
            print("Response is not valid JSON:", response.text[:200])
            return {}

    def load_last_id(self):
        if not os.path.exists(self.last_id_file):
            return None
        with open(self.last_id_file, 'r') as f:
            return f.read().strip()

    def save_last_id(self, transaction_id):
        with open(self.last_id_file, 'w') as f:
            f.write(str(transaction_id))

    def process_new_transactions(self, transactions):
        rows = transactions.get('rows', [])
        if not rows:
            print('No transactions found.')
            return

        latest_id = rows[0].get('id')
        last_saved = self.load_last_id()

        if str(latest_id) == str(last_saved):
            print('No new transactions.')
            return

        new_rows = []
        for row in rows:
            if str(row.get('id')) == str(last_saved):
                break
            new_rows.append(row)

        self.save_last_id(latest_id)
        print('New transactions:', new_rows)


def fetch_and_process_transactions():
    print(f"Running task at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    token = 'ZDVkMDg3MjYtZDBhYy00NDNkLWJjNzUtYTBhN2E2OTNlMGZk'
    service = TransactionService(session_token=token)

    start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    end = datetime.now()
    params = {
        'list': 'true',
        'pageSize': '50',
        'beginDate': start.strftime('%Y-%m-%d %H:%M:%S'),
        'endDate': end.strftime('%Y-%m-%d %H:%M:%S'),
        'limitCount': '100000',
        'pageList': 'true'
    }

    tx = service.get_transactions(params)
    service.process_new_transactions(tx)


if __name__ == '__main__':
    fetch_and_process_transactions()

    schedule.every(5).minutes.do(fetch_and_process_transactions)
    while True:
        schedule.run_pending()
        time.sleep(60)
