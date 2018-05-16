from authorizenet import apicontractsv1
from authorizenet.apicontrollers import *
from decimal import Decimal
from pecan import conf
from random import randint
from urbane.utils import decrypt
from urbane.verifiers import IVerifier

#import requests as req
import uuid

'''Auth.net credit card verifier'''


def resp2dict(o):
    d = {}
    for k in o.__dict__.keys():
        a = getattr(o, k)
        v = a.pyval if hasattr(a, 'pyval') else a
        try:
            d[k] = resp2dict(v)
        except:
            d[k] = v
    return d


class Verifier(IVerifier):

    def __init__(self, **config):
        super(Verifier, self).__init__()
        self.conf = config


    def verify(self, signup, **params):

        if not conf['enable_billing']:
            return 0

        amount = Decimal('1.00')

    	merchantAuth = apicontractsv1.merchantAuthenticationType()
    	merchantAuth.name = self.conf['api_login']
    	merchantAuth.transactionKey = self.conf['api_transact_key']

    	creditCard = apicontractsv1.creditCardType()
    	creditCard.cardNumber = decrypt(conf['database']['cipher_key'], signup.billing_cc_number)
    	creditCard.expirationDate = signup.billing_cc_expire

    	payment = apicontractsv1.paymentType()
    	payment.creditCard = creditCard

    	transactionrequest = apicontractsv1.transactionRequestType()
    	transactionrequest.transactionType = "authOnlyTransaction"
    	transactionrequest.amount = Decimal('1.00')
    	transactionrequest.payment = payment

    	createtransactionrequest = apicontractsv1.createTransactionRequest()
    	createtransactionrequest.merchantAuthentication = merchantAuth
    	#createtransactionrequest.refId = "MerchantID-00003" # % str(randint(1, 99999))

    	createtransactionrequest.transactionRequest = transactionrequest
    	createtransactioncontroller = createTransactionController(createtransactionrequest)

        for i in xrange(3): # do 3 attempts
            try:
                createtransactioncontroller.execute()
                break
            except:
                pass

    	response = createtransactioncontroller.getresponse()

        # store authorize.net response in extra
        print resp2dict(response)
        signup.extra['authnet'] = resp2dict(response)

    	return 1 if (response.messages.resultCode == "Ok" and response.transactionResponse.responseCode == 1) else -1
