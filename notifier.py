#!/usr/bin/env python
# This is a simple stock email notifier
import json
import time
import http.client


FILE_NAME = "config.json"

host = "yahoo-finance-low-latency.p.rapidapi.com"
api_key = "0123456789abcdefghijklmnopqrtsubwxyz0123456789abcde"
interval = 60
email = "max@example.com"
notifications = []


class Notification:
    def __init__(self, n):
        self.symbol = n['SYMBOL']
        self.price = n['PRICE']
        self.percentage = n['PERCENTAGE']
        self.current_price = None
        self.long = None
        self.notify = False

    def check_notification(self):
        if self.percentage == 0:
            if self.long & self.current_price > self.price:
                self.notify = True
            elif not self.long & self.current_price < self.price:
                self.notify = True
        else:
            div = self.percentage * self.price / 100
            # TODO calculate limits and notify


def create_report(notificytions):
    # TODO create email log report
    return


if __name__ == '__main__':
    try:
        # read config and initialize
        with open(FILE_NAME) as f:
            data = json.load(f)

        host = data['HOST']
        api_key = data['API_KEY']
        interval = data['INVTERVAL']
        email = data['EMAIL']

        for n in data['NOTIFICATIONS']:
            notifications.append(Notification(n))

        symbols = ""
        for n in notifications:
            symbols = "%s," % n.symbol

        # https connection
        conn = http.client.HTTPSConnection(host)
        headers = {
            'x-rapidapi-key': api_key,
            'x-rapidapi-host': host
        }

    except:
        SystemExit('Invalid configuration')

    while True:
        request = "/v6/finance/quote?symbols=%s&lang=en&region=US" % symbols
        conn.request("GET", request, headers=headers)
        res = conn.getresponse()

        for n in notifications:
            # TODO navigate to correct list entry
            n.current_price = res['regularMarketPrice']
            if n.long is None:
                n.long = n.current_price < n.price
            n.check_notification()

        create_report(notifications.__contains__(n.notify))
        time.sleep(interval * 60)


