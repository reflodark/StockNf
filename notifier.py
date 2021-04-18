# This is a simple stock email notifier
import json
import time
import logging
import urllib.parse
import http.client


FILE_NAME = "config.json"

host = "yahoo-finance-low-latency.p.rapidapi.com"
api_key = "123456789012345678901234567890123456789012345678901"
interval = 60
email = "max@example.com"
notifications = []


class Notification:
    def __init__(self, n):
        self.symbol = n['symbol']
        self.price = n['price']
        self.percentage = n['percentage']
        self.current_price = None
        self.long = None
        self.notify = False

    def check_notification(self):
        if self.current_price is None or self.long is None:
            return
        if self.percentage == 0:
            if self.long and self.current_price > self.price:
                self.notify = True
            elif not self.long and self.current_price < self.price:
                self.notify = True
        else:
            div = self.percentage * self.price / 100
            # TODO calculate limits and notify


def create_report(notificytions):
    # TODO create email and log report
    return


if __name__ == '__main__':
    logging.basicConfig(filename='notifier.log', level=logging.DEBUG)
    try:
        logging.info("start")
        # read file, init
        with open(FILE_NAME, 'r') as f:
            data = json.load(f)

        host = data['host']
        api_key = data['api_key']
        interval = data['interval']
        email = data['email']

        for n in data['notifications']:
            notifications.append(Notification(n))

        symbols = ""
        for n in notifications:
            symbols = symbols + "%s," % n.symbol
        symbols = symbols[:-1]
        symbols = urllib.parse.quote(symbols)
        logging.info(symbols)

        # https connection
        conn = http.client.HTTPSConnection(host)
        headers = {
            'x-rapidapi-key': api_key,
            'x-rapidapi-host': host
        }
        logging.info(headers)

        while True:
            request = "/v6/finance/quote?symbols=%s&lang=en&region=US" % symbols
            logging.info(request)
            conn.request("GET", request, headers=headers)
            res = conn.getresponse()
            data = res.read()
            data = data.decode()
            data = json.loads(data)
            logging.info(data)

            for i in range(len(notifications)):
                if len(notifications) != len(data['quoteResponse']['result']):
                    break
                if notifications[i].symbol != data['quoteResponse']['result'][i]['symbol']:
                    break

                notifications[i].current_price = data['quoteResponse']['result'][i]['regularMarketPrice']

                if notifications[i].long is None:
                    notifications[i].long = notifications[i].current_price < notifications[i].price
                notifications[i].check_notification()

            create_report(notifications.__contains__(n.notify))
            time.sleep(interval * 60)

    except Exception as e:
        logging.error("Exception occurred", exc_info=True)

