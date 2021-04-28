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
        self.long = None
        self.current_price = None
        self.reference_price = None
        self.last_reference_price = None
        self.margin_high = None
        self.margin_low = None
        self.notify = False

    def check_notification(self):
        if self.current_price is None or self.long is None:
            return
        if self.percentage == 0:
            if self.long and self.current_price > self.price:
                self.notify = True
                self.long = False
            elif not self.long and self.current_price < self.price:
                self.notify = True
                self.long = True
        else:
            self.margin_high = round(self.reference_price + self.price * self.percentage / 100)
            self.margin_low = round(self.reference_price - self.price * self.percentage / 100)
            self.margin_low = self.margin_low if self.margin_low > 0 else 0

            if self.margin_low > self.current_price or self.margin_high < self.current_price:
                self.notify = True
                self.last_reference_price = self.reference_price
                self.reference_price = self.current_price

        logging.info('Notification check: %s, %s' % (self.notify, self))

    def __str__(self):
        if self.percentage == 0:
            long = self.long if not self.notify else not self.long
            return 'Symbol:%s Price:%s Long:%s Current Price:%s' % (
                self.symbol,
                self.price,
                long,
                self.current_price)
        else:
            return 'Symbol:%s Price:%s Percentage:%s Current Price:%s Reference price:%s Margin l/h:%s/%s' % (
                self.symbol,
                self.price,
                self.percentage,
                self.current_price,
                self.last_reference_price,
                self.margin_low,
                self.margin_high)


def create_report(notifications):
    if not notifications:
        return
    message = 'Stock notification for: '
    for n in notifications:
        message += "\n%s" % n
        n.notify = False
    yag.send_unsent()
    yag.send(to=email_recipients, subject='StockNf', contents=message)
    logging.info("Email sent: %s" % message)


if __name__ == '__main__':
    logging.basicConfig(filename='notifier.log', format='%(asctime)s %(levelname)s %(message)s', level=logging.DEBUG)
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
                conn.connect()
                conn.request('GET', request, headers=headers)
                res = conn.getresponse()
                data = res.read()
                data = data.decode()
                data = json.loads(data)
                logging.info(data)

                i = 0
                for n in notifications:
                    # validation
                    if len(notifications) != len(data['quoteResponse']['result']):
                        logging.error('len: %s, %s' % (len(notifications), len(data['quoteResponse']['result'])))
                        break
                    if n.symbol != data['quoteResponse']['result'][i]['symbol']:
                        logging.error('symbol: %s, %s' % (n.symbol, data['quoteResponse']['result'][i]['symbol']))
                        break
                    # data handling
                    n.current_price = data['quoteResponse']['result'][i]['regularMarketPrice']
                    if n.reference_price is None:
                        n.reference_price = n.current_price
                        n.last_reference_price = n.reference_price
                    if n.long is None:
                        n.long = n.current_price < n.price
                    n.check_notification()
                    i += 1

                create_report([n for n in notifications if n.notify])
                conn.close()
            except http.client.HTTPException:
                logging.exception('HTTP exception', exc_info=True)
            except yagmail.YagConnectionClosed:
                logging.exception('Yagmail connection closed', exc_info=True)
                yag.login()

            if interval < 1:
                interval = 1
            time.sleep(interval * 60)

    except http.client.HTTPException:
        logging.exception('HTTP exception', exc_info=True)
    except yagmail.YagAddressError:
        logging.exception('YagAddressError', exc_info=True)
    except Exception:
        logging.critical('Exception occurred', exc_info=True)
    finally:
        conn.close()
        yag.close()
        logging.info('Exit')

