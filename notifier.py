# This is a simple stock email notifier
import json
import time
import logging
import urllib.parse
import http.client
import yagmail


FILE_NAME = 'config.json'

host = 'yahoo-finance-low-latency.p.rapidapi.com'
api_key = '123456789012345678901234567890123456789012345678901'
interval = 60
email_recipients = ['r1@example.com', 'r2@example.com']
email_sender = 'sender@example.com'
notifications = []


class Notification:
    def __init__(self, n):
        self.symbol = n['symbol']
        self.price = n['price']
        self.percentage = n['percentage']
        self.reference_price = None
        self.current_price = None
        self.long = None
        self.notify = False

    def check_notification(self):
        if self.current_price is None or self.long is None:
            return
        if self.percentage == 0:
            if self.long and self.current_price > self.price:
                self.notify = True
                self.long = False
                logging.info('N')
            elif not self.long and self.current_price < self.price:
                self.notify = True
                self.long = True
        else:
            margin_high = self.reference_price + self.price * self.percentage / 100
            margin_low = self.reference_price - self.price * self.percentage / 100
            margin_low = margin_low if margin_low > 0 else 0

            if margin_low > self.current_price or margin_high < self.current_price:
                self.notify = True
                self.reference_price = self.current_price

    def __str__(self):
        if self.percentage == 0:
            return 'Symbol:%s Price:%s Long:%s Current Price:%s' % (self.symbol, self.price, not self.long,
                                                                    self.current_price)
        else:
            return 'Symbol:%s Price:%s Percentage:%s Reference price:%s' % (self.symbol, self.price, self.percentage,
                                                                            self.reference_price)


def create_report(notifications):
    if not notifications:
        return
    message = 'Stock notification for: '
    for n in notifications:
        message += "\n%s" % n
        n.notify = False
    yag.send(to=email_recipients, subject='StockNf', contents=message)
    logging.info("Email sent: %s" % message)


if __name__ == '__main__':
    logging.basicConfig(filename='notifier.log', format='%(asctime)s %(message)s', level=logging.DEBUG)
    try:
        logging.info('start')
        # read file, init
        with open(FILE_NAME, 'r') as f:
            data = json.load(f)

        host = data['host']
        api_key = data['api_key']
        interval = data['interval']
        email_sender = data['email_sender']
        email_recipients = data['email_recipients']
        yag = yagmail.SMTP(email_sender)

        for n in data['notifications']:
            notifications.append(Notification(n))

        symbols = ''
        for n in notifications:
            symbols = symbols + '%s,' % n.symbol
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
                request = '/v6/finance/quote?symbols=%s&lang=en&region=US' % symbols
                conn.request('GET', request, headers=headers)
                res = conn.getresponse()
                data = res.read()
                data = data.decode()
                data = json.loads(data)
                logging.info(data)

                i = 0
                for n in notifications:
                    if len(notifications) != len(data['quoteResponse']['result']):
                        break
                    if n.symbol != data['quoteResponse']['result'][i]['symbol']:
                        break
                    n.current_price = data['quoteResponse']['result'][i]['regularMarketPrice']
                    if n.reference_price is None:
                        n.reference_price = data['quoteResponse']['result'][i]['regularMarketPrice']
                    if n.long is None:
                        n.long = n.current_price < n.price
                    n.check_notification()
                    i += 1

                create_report([n for n in notifications if n.notify])
            except http.client.HTTPException as e:
                logging.error('Http exception', exc_info=True)

            if interval < 1:
                interval = 1
            time.sleep(interval * 60)

    except Exception as e:
        logging.error('Exception occurred', exc_info=True)

