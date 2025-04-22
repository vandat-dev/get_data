import json
import os
import time
from datetime import datetime

import schedule
import urllib3
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class SeleniumLogin:
    def __init__(self, driver_path, base_url, username, password):
        service = Service(driver_path)
        opts = webdriver.ChromeOptions()
        opts.add_argument('--headless')
        opts.add_argument('--disable-gpu')
        opts.add_argument('--no-sandbox')
        opts.add_argument('--ignore-certificate-errors')
        self.driver = webdriver.Chrome(service=service, options=opts)
        self.base_url = base_url
        self.username = username
        self.password = password

    def login(self):
        self.driver.get(self.base_url)
        wait = WebDriverWait(self.driver, 10)
        wait.until(EC.presence_of_element_located((By.ID, "username"))).send_keys(self.username)
        wait.until(EC.presence_of_element_located((By.ID, "password"))).send_keys(self.password)
        wait.until(EC.element_to_be_clickable(
            (By.XPATH, "/html/body/div[1]/div/div/div[2]/div[2]/div/div/form/div[4]/button")
        )).click()
        wait.until(EC.url_changes(self.base_url))
        print("✅ Logged in, session alive.")


class TransactionService:
    def __init__(self, driver, base_url):
        self.driver = driver
        self.base_url = base_url
        self.last_id_file = 'last_user_id.txt'

    def get_transactions(self, params: dict):
        params_json = json.dumps(params)
        script = """
        const callback = arguments[arguments.length - 1];
        const base = arguments[0];
        const params = JSON.parse(arguments[1]);
        const body = new URLSearchParams(params).toString();

        fetch(base + "/attTransaction.do", {
            method: "POST",
            credentials: "include",
            headers: {
                "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
                "X-Requested-With": "XMLHttpRequest"
            },
            body: body
        })
        .then(res => {
            if (!res.ok) throw new Error("HTTP " + res.status);
            return res.json();
        })
        .then(data => callback(JSON.stringify({ ok: true, data })))
        .catch(err => callback(JSON.stringify({ ok: false, error: err.toString() })));
        """

        result_str = self.driver.execute_async_script(script, self.base_url, params_json)
        result = json.loads(result_str)

        if not result.get("ok"):
            raise RuntimeError("Fetch error: " + result.get("error", "unknown"))
        return result["data"]

    def load_last_id(self):
        if not os.path.exists(self.last_id_file):
            return None
        return open(self.last_id_file).read().strip()

    def save_last_id(self, txn_id):
        with open(self.last_id_file, 'w') as f:
            f.write(str(txn_id))

    def process_new_transactions(self, tx_json):
        rows = tx_json.get('rows', [])
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


def fetch_and_process(service: TransactionService):
    now = datetime.now()
    print(f"Running task at {now:%Y-%m-%d %H:%M:%S}")
    start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    end = now.replace(hour=23, minute=59, second=59)
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
    LOGIN_URL = "https://192.168.30.78:8098"
    DRIVER_PATH = "/usr/bin/chromedriver"
    USERNAME = "admin"
    PASSWORD = "rsC11111!"

    login = SeleniumLogin(DRIVER_PATH, LOGIN_URL, USERNAME, PASSWORD)
    login.login()

    svc = TransactionService(login.driver, LOGIN_URL)

    fetch_and_process(svc)
    schedule.every(5).minutes.do(fetch_and_process, svc)

    try:
        while True:
            schedule.run_pending()
            time.sleep(60)
    finally:
        login.driver.quit()
