from pyminfraud import Client
from pecan import conf, request
from urbane.model import Signup
from urbane.utils import decrypt, json_encode
from urbane.verifiers import IVerifier

'''MaxMind MinFroud Score verifier'''

class Verifier(IVerifier):

    def __init__(self, **config):
        super(Verifier, self).__init__()
        self.conf = config
        print self.conf


    def verify(self, signup, **params):

        print "MinFraud verifier"

        if not conf['enable_billing']:
            return 0

        contact_email = signup.contact_email.lower()
        (lastname, first_name) = signup.contact_person.replace(' ', '').split(',')
        (address, city, region, postal, country) = signup.billing_address.split(', ')
        credit_card = decrypt(conf['database']['cipher_key'], signup.billing_cc_number)
        cvv_result = params['billing_cc_secret'] if 'billing_cc_secret' in params else None

        # prepare request data
        fields = {

            'ip': request.remote_addr,

            'billing_city': city,
            'billing_state': region,
            'billing_country': country,
            'billing_zip': postal,
            'bin_cardnumber': credit_card,
            'session_language': request.accept_language,
            'session_useragent': request.user_agent,
            'user_domain': contact_email.split('@')[1],
            'user_login': signup.username,
            'user_password': decrypt(conf['database']['cipher_key'], signup.password),
            'user_phone': signup.contact_phone,
            'user_email': contact_email,
            #'cc_avs'
            #'cc_cvv'
        }

        minfraud = Client(self.conf['license_key'])
        minfraud.add_fields(fields)
        result = minfraud.execute()
        riskScore = float(result['riskScore'])
        signup.extra['minfraud'] = result
        if riskScore <= self.conf['accept_risk_score']:
            return 1
        elif riskScore <= self.conf['reject_risk_score']:
            return 0
        else:
            return self.conf['fraud_decrement']

        try:
            # perform minfraud score request
            minfraud = Client(self.conf['license_key'])
            minfraud.add_fields(fields)
            result = minfraud.execute()
            riskScore = float(result['riskScore'])
            signup.minfraud_fields = fields
            signup.minfraud_result = result
            signup.save()
            if riskScore <= self.conf['accept_risk_score']:
                return 1
            elif riskScore <= self.conf['reject_risk_score']:
                return 0
            else:
                return self.conf['fraud_decrement']
        except:
            # do not change signup score on error
            return 0
