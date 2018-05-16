from pecan import conf
from urbane.utils import decrypt
from urbane.verifiers import IVerifier

'''Luhn credit card number checksum verifier'''

def digits_of(number):
    return list(map(int, str(number)))

def luhn_checksum(cc_number):
    digits = digits_of(cc_number)
    odd_digits = digits[-1::-2]
    even_digits = digits[-2::-2]
    total = sum(odd_digits)
    for digit in even_digits:
        total += sum(digits_of(2 * digit))
    return total % 10

class Verifier(IVerifier):

    def __init__(self, **config):
        super(Verifier, self).__init__()
        self.conf = config

    def verify(self, signup, **params):

        if not conf['enable_billing']:
            return 0

        return 1 if luhn_checksum(decrypt(signup.billing_cc_number)) == 0 else -1
