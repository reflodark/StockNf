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

    def __str__(self):
        return "Symbol:%s Price:%s Percentage:%s Long:%s" % (self.symbol, self.price, self.percentage, self.long)


def create_report(notificytions):
    if len(notificytions) < 1:
        return
    message = "Stock notification for: "
    for n in notifications:
        message += "\n%s" % n
        n.notify = False
    logging.info(message)


if __name__ == '__main__':
    logging.basicConfig(filename='notifier.log', format='%(asctime)s %(message)s', level=logging.DEBUG)
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

        while True:
            try:
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

                create_report([n for n in notifications if n.notify])
            except http.client.HTTPException as e:
                logging.error("Http exception", exc_info=True)
            except Exception as e:
                logging.error("Exception exception", exc_info=True)

            if interval < 1:
                interval = 1
            time.sleep(interval * 60)

    except Exception as e:
        logging.error("Exception occurred", exc_info=True)

