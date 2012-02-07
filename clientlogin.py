from urllib2 import urlopen, Request
from urllib2 import HTTPError
from urllib import urlencode

try:
    input = raw_input
except NameError:
    input = input

class ClientLogin:
    AUTH_URL = 'https://www.google.com/accounts/ClientLogin'

    def __init__(self, user, passwd, service, acct_type='GOOGLE', source=None):
        self.user = user
        self.passwd = passwd
        self.service = service
        self.acct_type = acct_type
        self.source = source

        self.auth_token = None

    def _process_response(self, resp):
        ret = {}
        for line in resp.split('\n'):
            if '=' in line:
                var, val = line.split('=', 1)
                ret[var] = val
        return ret

    def _make_request(self, url, data, headers):
        data = urlencode(data)
        if data == '':
            data = None
        else:
            data = data.encode('utf8')

        req = Request(url, data, headers)
        err = None

        try:
            resp_obj = urlopen(req)
        except HTTPError as e:
            err = e.code
            return err, e.read()
        resp = resp_obj.read()
        resp_obj.close()
        return None, unicode(resp, encoding='utf8')

    def request_auth_token(self):
        data = {
            'Email':        self.user,
            'Passwd':       self.passwd,
            'accountType':  self.acct_type,
            'service':      self.service
        }
        if self.source:
            data['source'] = self.source

        headers = {
            'Content-Type':     'application/x-www-form-urlencoded;charset=utf-8'
        }
        err, resp = self._make_request(self.AUTH_URL, data, headers)
        if err is not None:
            raise "HTTP Error %d" % err

        ret = self._process_response(resp)
        if 'Auth' in ret:
            self.auth_token = ret['Auth']
            return ret['Auth']
        if 'Error' not in ret:
            raise 'Unknown Error!'
        else:
            raise ret['Error']

    def get_auth_token(self, request=False):
        if self.auth_token is None and request is False:
            return None
        elif self.auth_token is None:
            return self.request_auth_token()
        return self.auth_token

if __name__ == '__main__':
    print('Please enter your Google username:')
    user = raw_input()
    print('Please enter your password:')
    passwd = raw_input()

    client = ClientLogin(user, passwd, 'sj')
    print('Your auth token is: %s' % client.request_auth_token())
