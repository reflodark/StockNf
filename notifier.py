#!/usr/bin/env python3
# This is a simple quote email notifier

import json
import time
import logging
import urllib.parse
import http.client
import yagmail

CONFIG_FILE = 'config.json'
RECOVERY_FILE = 'recovery.json'

host = 'yahoo-finance-low-latency.p.rapidapi.com'
api_key = '123456789012345678901234567890123456789012345678901'
interval = 60
email_recipients = ['r1@example.com', 'r2@example.com']
email_sender = 'sender@example.com'
notifications = []


class Notification:
    def __init__(self, n):
        '''
        Notification constructor
        :param n: Dictionary from config file
        '''
        self.symbol = n['symbol']
        self.price = n['price'] if 'price' in n else None
        self.percentage = n['percentage'] if 'percentage' in n else None
        self.spread = n['spread'] if 'spread' in n else None
        self.long = None
        self.current_price = None
        self.reference_price = None
        self.last_reference_price = None
        self.margin_high = None
        self.margin_low = None
        self.notify = False

        assert self.price != 0 or self.percentage != 0 or self.spread != 0, 'invalid configuration'

    def check_notification(self):
        '''
        Check if it's necessary to notify for each possible setting
        :return:
        '''
        if self.current_price is None:
            return

        # Fixed price limit
        if self.price != 0 and self.price is not None:
            if self.long and self.current_price > self.price:
                self.notify = True
                self.long = False
            elif not self.long and self.current_price < self.price:
                self.notify = True
                self.long = True

        # Percentage of reference price
        if self.percentage != 0 and self.percentage is not None:
            self.margin_high = self.reference_price + self.reference_price * self.percentage / 100
            self.margin_low = self.reference_price - self.reference_price * self.percentage / 100
            self.margin_low = self.margin_low if self.margin_low > 0 else 0

            if self.margin_low > self.current_price or self.margin_high < self.current_price:
                self.notify = True

        # Fixed price spread / span
        if self.spread != 0 and self.spread is not None:
            if self.reference_price - self.spread > self.current_price \
                    or self.reference_price + self.spread < self.current_price:
                self.notify = True

        if self.notify:
            self.last_reference_price = self.reference_price
            self.reference_price = self.current_price

        logging.info('Notification check: %s, %s' % (self.notify, self))

    def get_recovery_data(self):
        '''
        Get recovery data as a dictionary
        :return:
        '''
        return {'symbol': self.symbol,
                'price': self.price,
                'percentage': self.percentage,
                'spread': self.spread,
                'long': self.long,
                'reference_price': self.reference_price,
                'last_reference_price': self.last_reference_price}

    def set_recovery_data(self, rd):
        '''
        Try to load recovery data after a restart
        :param rd: Dictionary from recovery file
        :return:
        '''
        price = rd['price'] if 'price' in rd else None
        percentage = rd['percentage'] if 'percentage' in rd else None
        spread = rd['spread'] if 'spread' in rd else None
        if (self.symbol == rd['symbol']
                and self.price == price
                and self.percentage == percentage
                and self.spread == spread):
            self.reference_price = rd['reference_price']
            self.last_reference_price = rd['last_reference_price']
            logging.info('Recovery data set for %s' % self)

    def __str__(self):
        reference_price = self.reference_price if not self.notify else self.last_reference_price
        return 'Symbol:%s Price:%s Percentage:%s Spread: %s Current Price:%s Reference price:%s Margin l/h:%s/%s' % (
            self.symbol,
            self.price,
            self.percentage,
            self.spread,
            self.current_price,
            reference_price,
            self.margin_low,
            self.margin_high)


def create_report(notifications):
    '''
    Send reports via mail and create recovery data from notifications
    :param notifications: Notifications where the notify attribute is true
    :return:
    '''
    if not notifications:
        return

    # Create report and send mail
    message = 'Quote notification for:\n'
    for n in notifications:
        message += '\n%s\n' % n
        n.notify = False
    yag.send_unsent()
    yag.send(to=email_recipients, subject='QuoteNf', contents=message)
    logging.info('Email sent:\n%s' % message)

    # Serialize as JSON
    try:
        nfs = [n.get_recovery_data() for n in notifications]
        with open(RECOVERY_FILE, 'w') as f:
            json.dump(nfs, f)
    except EnvironmentError:
        logging.exception('Could not serialize notifications', exc_info=True)
    else:
        logging.info('Notifications serialized')


if __name__ == '__main__':
    logging.basicConfig(filename='notifier.log', format='%(asctime)s %(levelname)s %(message)s', level=logging.DEBUG)
    conn = None
    try:
        logging.info('start')
        # read config, init
        with open(CONFIG_FILE, 'r') as f:
            data = json.load(f)

        host = data['host']
        api_key = data['api_key']
        interval = data['interval']
        email_sender = data['email_sender']
        email_recipients = data['email_recipients']
        yag = yagmail.SMTP(email_sender)
        for n in data['notifications']:
            notifications.append(Notification(n))

        # read / deserialize notifications (JSON) and merge data
        try:
            with open(RECOVERY_FILE, 'r') as f:
                recovery_data = json.load(f)
        except FileNotFoundError:
            logging.info('No recovery file found')
        else:
            for notification in notifications:
                for rd in recovery_data:
                    notification.set_recovery_data(rd)

        # filter symbols and parse to charset
        symbols = set((n.symbol for n in notifications))
        symbols = ','.join(symbols)
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
                # connect and read quotes
                request = '/v6/finance/quote?symbols=%s&lang=en&region=US' % symbols
                conn.connect()
                conn.request('GET', request, headers=headers)
                res = conn.getresponse()
                data = res.read()
                data = data.decode()
                data = json.loads(data)
                logging.info(data)

                for n in notifications:
                    # get corresponding symbol
                    res = None
                    for d in data['quoteResponse']['result']:
                        if d['symbol'] == n.symbol:
                            res = d
                            break

                    # validation
                    if res is None:
                        logging.error('symbol %s not in response', n.symbol)
                        continue

                    # data handling
                    n.current_price = res['regularMarketPrice']
                    if n.reference_price is None or n.last_reference_price is None:
                        n.reference_price = n.current_price
                        n.last_reference_price = n.reference_price
                    if n.long is None and n.price is not None:
                        n.long = n.current_price < n.price
                    n.check_notification()

                # report, serialize notifications and close connection (to prevent timeout)
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
        logging.error('Exception occurred', exc_info=True)
    finally:
        logging.info('Exit')
