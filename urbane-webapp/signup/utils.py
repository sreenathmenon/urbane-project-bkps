try:
    from ConfigParser import ConfigParser
except ImportError:
    from configparser import ConfigParser
except:
    raise

from collections import OrderedDict
from datetime import datetime
from pytz import timezone, all_timezones as timezones

import operator
import re

# Config helpers
def parse_num(v):
    try:
        return int(v)
    except ValueError:
        try:
            return float(v)
        except ValueError:
            return v

true_values = [True, 'true', 'True', 'TRUE', 'yes', 'Yes', 'YES', 'on', 'On', 'ON']
false_values = [False, 'false', 'False', 'FALSE', 'no', 'No', 'NO', 'off', 'Off', 'OFF']

# `extended` ConfigParser
class Config(ConfigParser):

    def __getitem__(self, section):
        return dict(self.items(section))

    def as_dict(self):

        _dict_ = {}

        # parse primitives
        for section in self.sections():

            items = {}

            for key, val in self.items(section):
                # parse strings
                if (val[0] == '"' and val[-1] == '"') or (val[0] == "'" and val[-1] == "'"):
                    items[key] = val[1:-1]
                # parse lists
                elif isinstance(val, basestring) and ',' in val:
                    items[key] = re.sub('\s?,\s?', ',', val).split(',')
                # parse bools
                elif val in true_values:
                    items[key] = True
                elif val in false_values:
                    items[key] = False
                # parse integers
                else:
                    items[key] = parse_num(val)

            items['__force_dict__'] = True
            _dict_[section] = items

        _dict_.update(_dict_.pop('default'))

        if not 'enable_billing' in _dict_:
            _dict_['enable_billing'] = True

        return _dict_


def tzlist():
    result = OrderedDict()
    for tzname in timezones:
        tz = timezone(tzname)
        result[tzname] = '(GMT%s) %s' % (datetime.now(tz).strftime("%z"), tzname)
    return result

# contry names and phone codes
_countries_ = {
    "AF": { "name": "Afghanistan", "code": "93" },
    "AL": { "name": "Albania", "code": "355" },
    "DZ": { "name": "Algeria", "code": "213" },
    "AS": { "name": "American Samoa", "code": "1-684" },
    "AD": { "name": "Andorra", "code": "376" },
    "AO": { "name": "Angola", "code": "244" },
    "AI": { "name": "Anguilla", "code": "1-264" },
    "AQ": { "name": "Antarctica", "code": "672" },
    "AG": { "name": "Antigua and Barbuda", "code": "1-268" },
    "AR": { "name": "Argentina", "code": "54" },
    "AM": { "name": "Armenia", "code": "374" },
    "AW": { "name": "Aruba", "code": "297" },
    "AU": { "name": "Australia", "code": "61" },
    "AT": { "name": "Austria", "code": "43" },
    "AZ": { "name": "Azerbaijan", "code": "994" },
    "BS": { "name": "Bahamas", "code": "1-242" },
    "BH": { "name": "Bahrain", "code": "973" },
    "BD": { "name": "Bangladesh", "code": "880" },
    "BB": { "name": "Barbados", "code": "1-246" },
    "BY": { "name": "Belarus", "code": "375" },
    "BE": { "name": "Belgium", "code": "32" },
    "BZ": { "name": "Belize", "code": "501" },
    "BJ": { "name": "Benin", "code": "229" },
    "BM": { "name": "Bermuda", "code": "1-441" },
    "BT": { "name": "Bhutan", "code": "975" },
    "BO": { "name": "Bolivia", "code": "591" },
    "BQ": { "name": "Bonaire", "code": "599" },
    "BA": { "name": "Bosnia and Herzegovina", "code": "387" },
    "BW": { "name": "Botswana", "code": "267" },
    "BV": { "name": "Bouvet Island", "code": "47" },
    "BR": { "name": "Brazil", "code": "55" },
    "IO": { "name": "British Indian Ocean Territory", "code": "246" },
    "BN": { "name": "Brunei Darussalam", "code": "673" },
    "BG": { "name": "Bulgaria", "code": "359" },
    "BF": { "name": "Burkina Faso", "code": "226" },
    "BI": { "name": "Burundi", "code": "257" },
    "KH": { "name": "Cambodia", "code": "855" },
    "CM": { "name": "Cameroon", "code": "237" },
    "CA": { "name": "Canada", "code": "1" },
    "CV": { "name": "Cape Verde", "code": "238" },
    "KY": { "name": "Cayman Islands", "code": "1-345" },
    "CF": { "name": "Central African Republic", "code": "236" },
    "TD": { "name": "Chad", "code": "235" },
    "CL": { "name": "Chile", "code": "56" },
    "CN": { "name": "China", "code": "86" },
    "CX": { "name": "Christmas Island", "code": "61" },
    "CC": { "name": "Cocos (Keeling) Islands", "code": "61" },
    "CO": { "name": "Colombia", "code": "57" },
    "KM": { "name": "Comoros", "code": "269" },
    "CG": { "name": "Congo", "code": "242" },
    "CD": { "name": "Democratic Republic of the Congo", "code": "243" },
    "CK": { "name": "Cook Islands", "code": "682" },
    "CR": { "name": "Costa Rica", "code": "506" },
    "HR": { "name": "Croatia", "code": "385" },
    "CU": { "name": "Cuba", "code": "53" },
    "CW": { "name": "Curacao", "code": "599" },
    "CY": { "name": "Cyprus", "code": "357" },
    "CZ": { "name": "Czech Republic", "code": "420" },
    "CI": { "name": "Cote d'Ivoire", "code": "225" },
    "DK": { "name": "Denmark", "code": "45" },
    "DJ": { "name": "Djibouti", "code": "253" },
    "DM": { "name": "Dominica", "code": "1-767" },
    "DO": { "name": "Dominican Republic", "code": "1-809" },
    "EC": { "name": "Ecuador", "code": "593" },
    "EG": { "name": "Egypt", "code": "20" },
    "SV": { "name": "El Salvador", "code": "503" },
    "GQ": { "name": "Equatorial Guinea", "code": "240" },
    "ER": { "name": "Eritrea", "code": "291" },
    "EE": { "name": "Estonia", "code": "372" },
    "ET": { "name": "Ethiopia", "code": "251" },
    "FK": { "name": "Falkland Islands (Malvinas)", "code": "500" },
    "FO": { "name": "Faroe Islands", "code": "298" },
    "FJ": { "name": "Fiji", "code": "679" },
    "FI": { "name": "Finland", "code": "358" },
    "FR": { "name": "France", "code": "33" },
    "GF": { "name": "French Guiana", "code": "594" },
    "PF": { "name": "French Polynesia", "code": "689" },
    "TF": { "name": "French Southern Territories", "code": "262" },
    "GA": { "name": "Gabon", "code": "241" },
    "GM": { "name": "Gambia", "code": "220" },
    "GE": { "name": "Georgia", "code": "995" },
    "DE": { "name": "Germany", "code": "49" },
    "GH": { "name": "Ghana", "code": "233" },
    "GI": { "name": "Gibraltar", "code": "350" },
    "GR": { "name": "Greece", "code": "30" },
    "GL": { "name": "Greenland", "code": "299" },
    "GD": { "name": "Grenada", "code": "1-473" },
    "GP": { "name": "Guadeloupe", "code": "590" },
    "GU": { "name": "Guam", "code": "1-671" },
    "GT": { "name": "Guatemala", "code": "502" },
    "GG": { "name": "Guernsey", "code": "44" },
    "GN": { "name": "Guinea", "code": "224" },
    "GW": { "name": "Guinea-Bissau", "code": "245" },
    "GY": { "name": "Guyana", "code": "592" },
    "HT": { "name": "Haiti", "code": "509" },
    "HM": { "name": "Heard Island and McDonald Mcdonald Islands", "code": "672" },
    "VA": { "name": "Holy See (Vatican City State)", "code": "379" },
    "HN": { "name": "Honduras", "code": "504" },
    "HK": { "name": "Hong Kong", "code": "852" },
    "HU": { "name": "Hungary", "code": "36" },
    "IS": { "name": "Iceland", "code": "354" },
    "IN": { "name": "India", "code": "91" },
    "ID": { "name": "Indonesia", "code": "62" },
    "IR": { "name": "Iran, Islamic Republic of", "code": "98" },
    "IQ": { "name": "Iraq", "code": "964" },
    "IE": { "name": "Ireland", "code": "353" },
    "IM": { "name": "Isle of Man", "code": "44" },
    "IL": { "name": "Israel", "code": "972" },
    "IT": { "name": "Italy", "code": "39" },
    "JM": { "name": "Jamaica", "code": "1-876" },
    "JP": { "name": "Japan", "code": "81" },
    "JE": { "name": "Jersey", "code": "44" },
    "JO": { "name": "Jordan", "code": "962" },
    "KZ": { "name": "Kazakhstan", "code": "7" },
    "KE": { "name": "Kenya", "code": "254" },
    "KI": { "name": "Kiribati", "code": "686" },
    "KP": { "name": "Korea, Democratic People's Republic of", "code": "850" },
    "KR": { "name": "Korea, Republic of", "code": "82" },
    "KW": { "name": "Kuwait", "code": "965" },
    "KG": { "name": "Kyrgyzstan", "code": "996" },
    "LA": { "name": "Lao People's Democratic Republic", "code": "856" },
    "LV": { "name": "Latvia", "code": "371" },
    "LB": { "name": "Lebanon", "code": "961" },
    "LS": { "name": "Lesotho", "code": "266" },
    "LR": { "name": "Liberia", "code": "231" },
    "LY": { "name": "Libya", "code": "218" },
    "LI": { "name": "Liechtenstein", "code": "423" },
    "LT": { "name": "Lithuania", "code": "370" },
    "LU": { "name": "Luxembourg", "code": "352" },
    "MO": { "name": "Macao", "code": "853" },
    "MK": { "name": "Macedonia, the Former Yugoslav Republic of", "code": "389" },
    "MG": { "name": "Madagascar", "code": "261" },
    "MW": { "name": "Malawi", "code": "265" },
    "MY": { "name": "Malaysia", "code": "60" },
    "MV": { "name": "Maldives", "code": "960" },
    "ML": { "name": "Mali", "code": "223" },
    "MT": { "name": "Malta", "code": "356" },
    "MH": { "name": "Marshall Islands", "code": "692" },
    "MQ": { "name": "Martinique", "code": "596" },
    "MR": { "name": "Mauritania", "code": "222" },
    "MU": { "name": "Mauritius", "code": "230" },
    "YT": { "name": "Mayotte", "code": "262" },
    "MX": { "name": "Mexico", "code": "52" },
    "FM": { "name": "Micronesia, Federated States of", "code": "691" },
    "MD": { "name": "Moldova, Republic of", "code": "373" },
    "MC": { "name": "Monaco", "code": "377" },
    "MN": { "name": "Mongolia", "code": "976" },
    "ME": { "name": "Montenegro", "code": "382" },
    "MS": { "name": "Montserrat", "code": "1-664" },
    "MA": { "name": "Morocco", "code": "212" },
    "MZ": { "name": "Mozambique", "code": "258" },
    "MM": { "name": "Myanmar", "code": "95" },
    "NA": { "name": "Namibia", "code": "264" },
    "NR": { "name": "Nauru", "code": "674" },
    "NP": { "name": "Nepal", "code": "977" },
    "NL": { "name": "Netherlands", "code": "31" },
    "NC": { "name": "New Caledonia", "code": "687" },
    "NZ": { "name": "New Zealand", "code": "64" },
    "NI": { "name": "Nicaragua", "code": "505" },
    "NE": { "name": "Niger", "code": "227" },
    "NG": { "name": "Nigeria", "code": "234" },
    "NU": { "name": "Niue", "code": "683" },
    "NF": { "name": "Norfolk Island", "code": "672" },
    "MP": { "name": "Northern Mariana Islands", "code": "1-670" },
    "NO": { "name": "Norway", "code": "47" },
    "OM": { "name": "Oman", "code": "968" },
    "PK": { "name": "Pakistan", "code": "92" },
    "PW": { "name": "Palau", "code": "680" },
    "PS": { "name": "Palestine, State of", "code": "970" },
    "PA": { "name": "Panama", "code": "507" },
    "PG": { "name": "Papua New Guinea", "code": "675" },
    "PY": { "name": "Paraguay", "code": "595" },
    "PE": { "name": "Peru", "code": "51" },
    "PH": { "name": "Philippines", "code": "63" },
    "PN": { "name": "Pitcairn", "code": "870" },
    "PL": { "name": "Poland", "code": "48" },
    "PT": { "name": "Portugal", "code": "351" },
    "PR": { "name": "Puerto Rico", "code": "1" },
    "QA": { "name": "Qatar", "code": "974" },
    "RO": { "name": "Romania", "code": "40" },
    "RU": { "name": "Russian Federation", "code": "7" },
    "RW": { "name": "Rwanda", "code": "250" },
    "RE": { "name": "Reunion", "code": "262" },
    "BL": { "name": "Saint Barthelemy", "code": "590" },
    "SH": { "name": "Saint Helena", "code": "290" },
    "KN": { "name": "Saint Kitts and Nevis", "code": "1-869" },
    "LC": { "name": "Saint Lucia", "code": "1-758" },
    "MF": { "name": "Saint Martin (French part)", "code": "590" },
    "PM": { "name": "Saint Pierre and Miquelon", "code": "508" },
    "VC": { "name": "Saint Vincent and the Grenadines", "code": "1-784" },
    "WS": { "name": "Samoa", "code": "685" },
    "SM": { "name": "San Marino", "code": "378" },
    "ST": { "name": "Sao Tome and Principe", "code": "239" },
    "SA": { "name": "Saudi Arabia", "code": "966" },
    "SN": { "name": "Senegal", "code": "221" },
    "RS": { "name": "Serbia", "code": "381" },
    "SC": { "name": "Seychelles", "code": "248" },
    "SL": { "name": "Sierra Leone", "code": "232" },
    "SG": { "name": "Singapore", "code": "65" },
    "SX": { "name": "Sint Maarten (Dutch part)", "code": "1-721" },
    "SK": { "name": "Slovakia", "code": "421" },
    "SI": { "name": "Slovenia", "code": "386" },
    "SB": { "name": "Solomon Islands", "code": "677" },
    "SO": { "name": "Somalia", "code": "252" },
    "ZA": { "name": "South Africa", "code": "27" },
    "GS": { "name": "South Georgia and the South Sandwich Islands", "code": "500" },
    "SS": { "name": "South Sudan", "code": "211" },
    "ES": { "name": "Spain", "code": "34" },
    "LK": { "name": "Sri Lanka", "code": "94" },
    "SD": { "name": "Sudan", "code": "249" },
    "SR": { "name": "Suriname", "code": "597" },
    "SJ": { "name": "Svalbard and Jan Mayen", "code": "47" },
    "SZ": { "name": "Swaziland", "code": "268" },
    "SE": { "name": "Sweden", "code": "46" },
    "CH": { "name": "Switzerland", "code": "41" },
    "SY": { "name": "Syrian Arab Republic", "code": "963" },
    "TW": { "name": "Taiwan, Province of China", "code": "886" },
    "TJ": { "name": "Tajikistan", "code": "992" },
    "TZ": { "name": "United Republic of Tanzania", "code": "255" },
    "TH": { "name": "Thailand", "code": "66" },
    "TL": { "name": "Timor-Leste", "code": "670" },
    "TG": { "name": "Togo", "code": "228" },
    "TK": { "name": "Tokelau", "code": "690" },
    "TO": { "name": "Tonga", "code": "676" },
    "TT": { "name": "Trinidad and Tobago", "code": "1-868" },
    "TN": { "name": "Tunisia", "code": "216" },
    "TR": { "name": "Turkey", "code": "90" },
    "TM": { "name": "Turkmenistan", "code": "993" },
    "TC": { "name": "Turks and Caicos Islands", "code": "1-649" },
    "TV": { "name": "Tuvalu", "code": "688" },
    "UG": { "name": "Uganda", "code": "256" },
    "UA": { "name": "Ukraine", "code": "380" },
    "AE": { "name": "United Arab Emirates", "code": "971" },
    "GB": { "name": "United Kingdom", "code": "44" },
    "US": { "name": "United States", "code": "1" },
    "UM": { "name": "United States Minor Outlying Islands", "code": "1" },
    "UY": { "name": "Uruguay", "code": "598" },
    "UZ": { "name": "Uzbekistan", "code": "998" },
    "VU": { "name": "Vanuatu", "code": "678" },
    "VE": { "name": "Venezuela", "code": "58" },
    "VN": { "name": "Viet Nam", "code": "84" },
    "VG": { "name": "British Virgin Islands", "code": "1-284" },
    "VI": { "name": "US Virgin Islands", "code": "1-340" },
    "WF": { "name": "Wallis and Futuna", "code": "681" },
    "EH": { "name": "Western Sahara", "code": "212" },
    "YE": { "name": "Yemen", "code": "967" },
    "ZM": { "name": "Zambia", "code": "260" },
    "ZW": { "name": "Zimbabwe", "code": "263" },
    "AX": { "name": "Aland Islands", "code": "358" }
}

def countries():
    data = {}
    for code, item in _countries_.iteritems():
        data[code] = item['name']
    # order by country name
    data = OrderedDict(sorted(data.items(), key=operator.itemgetter(1)))
    return data

def codes():
    data = {}
    for code, item in _countries_.iteritems():
        data['(+%s)' % item['code']] = item['name']
    # order by country name
    data = OrderedDict(sorted(data.items(), key=operator.itemgetter(0)))
    return data
