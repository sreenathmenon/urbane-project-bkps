#
# signups storage
#
from datetime import datetime, timedelta
#from dateutil.parser import parse as parse_date
#from dateutil.tz import gettz
from inspect import getmembers, isroutine
from peewee import *
from playhouse.db_url import connect, register_database

from pecan import conf
from urbane.utils import json_decode, json_encode

from time import sleep

import logging
import traceback
import uuid

log = logging.getLogger(__name__)

#
# implement MySQL DB driver with reconnection on OperationalError
#
class MySQLRetryDatabase(MySQLDatabase):
    def execute_sql(self, sql, params=None, require_commit=True):
        cursor = None
        while not cursor:
            try:
                cursor = super(MySQLRetryDatabase, self).execute_sql(sql, params, require_commit)
            except OperationalError:
                if not self.is_closed():
                    self.close()
                try:
                    cursor = self.get_cursor()
                    cursor.execute(sql, params or ())
                    if require_commit and self.get_autocommit():
                        self.commit()
                except OperationalError:
                    cursor = None
                    sleep(5)
                    continue
        return cursor

register_database(MySQLRetryDatabase, 'mysql')


# prepare connection
db = connect(conf['database']['connection'])

while True:
    try:
        log.info('Connecting database...')
        db.connect()
        if db:
            break
    except:
        log.error(traceback.format_exc())
        # take a break for 5 secconds
        sleep(5)


# JSON field (used for `datum`)
class JSONField(TextField):

    _value_ = {}

    def db_value(self, v):
        _value_ = v
        return json_encode(_value_)

    def python_value(self, v):
        try:
            _value_ = json_decode(v or "{}")
            return _value_
        except:
            log.error(traceback.format_exc())
            return None

    def __setitem__(self, f, v):
        self._value_[f] = v

    def __getitem__(self, f):
        return self._value_.get(f, None)

    def __delitem__(seld, f):
        del self._value_[f]

    #NOTE: implement iterator if needed


# Signup model
# NOTE(div): keep in sync with urbaneclient.client.Signup
class Signup(Model):

    # id
    id = CharField(max_length=32, primary_key=True)
    # account username
    username = CharField(unique=True)
    # account password
    password = CharField()
    # create date
    cdate = CharField(max_length=19)
    # verification score
    score = IntegerField(default=0)
    # state
    state = CharField(default='N', max_length=1)
    # extra data
    extra = JSONField(null=True)
    # datum
    datum = JSONField(null=True)

    # constructor
    def __init__(self, **kwargs):
        super(Signup, self).__init__()
        # handle `datum`
        datum = kwargs.copy()
        for f in Signup._fields_:
            v = datum.pop(f, None)
            if v: setattr(self, f, v)
        self.datum = datum

    # proxy access to `datum` fields
    def __getattr__(self, f):
        if f[0] == '_' or f in Signup._fields_:
            return super(Signup, self).__getattr__(f)
        else:
            return self.datum.get(f, None)

    def __setattr__(self, f, v):
        if f[0] == '_' or f in Signup._fields_:
            super(Signup, self).__setattr__(f, v)
        else:
            self.datum[f] = v

    def __delattr__(self, f):
        if f[0] == '_' or f in Signup._fields_:
            super(Signup, self).__delattr__(f, v)
        else:
            del self.datum[f]

    # convert signup instance into dict
    def as_dict(self, plain=True):
        _dict_ = dict([(f, getattr(self, f)) for f in Signup._fields_])
        if plain:
            _dict_.update(_dict_.pop('datum'))
        return _dict_

    # create new or update existing signup
    @classmethod
    def store(cls, **kwargs):
        id = kwargs.pop('id', None)
        if id:
            
            # update existing instance
            signup = Signup.get(Signup.id == id)
            for f in kwargs.keys():
                setattr(signup, f, kwargs[f])
            Signup.update(**signup.as_dict(plain=False)).where(Signup.id == id).execute()

        else:
            # create new instance
            id = str(uuid.uuid4()).replace('-', '')
            kwargs['cdate'] = datetime.strftime(datetime.utcnow(), conf.datetime_store_format)
            Signup.create(id=id, **kwargs)
        return id

    # construct where clause
    @classmethod
    def _prepare_where_(cls, **kwargs):

        _since_ = kwargs.pop('since', None)
        _until_ = kwargs.pop('until', None)
        _cdate_ = kwargs.pop('cdate', None)
        _state_ = kwargs.pop('state', None)
        _where_ = None

        filter = lambda expr: _where_ & expr if _where_ else expr

        if _since_:
            if type(_since_) in [str, unicode]:
                _since_ = datetime.strptime(_since_, conf.date_format)
            _where_ = filter(Signup.cdate >= _since_)

        if _until_:
            if type(_until_) in [str, unicode]:
                _until_ = datetime.strptime(_until_, conf.date_format)
            _where_ = filter(Signup.cdate <= _until_)

        if _cdate_:
            if type(_cdate_) in [str, unicode]:
                _cdate_ = parse_date(_cdate_)
            _where_ = filter(Signup.cdate >= _cdate_)
            _where_ = filter(Signup.cdate < _cdate_ + timedelta(days=1))

        if _state_:
            _where_ = filter(Signup.state << list(_state_.replace(' ', '').replace(',', '').replace('|', '').upper()))

        return _where_


    # fetch signup(s)
    @classmethod
    def fetch(cls, id=None, **kwargs):
        #id = kwargs.get('id', None)
        if id:
            # fetch sole signup
            try:
                signup = Signup.get(Signup.id == id)
                # convert cdate to datetime
                signup.cdate = datetime.strptime(signup.cdate, conf.datetime_store_format)
                return signup
            except:
                return None

        # fetch list of signups
        _where_ = Signup._prepare_where_(**kwargs)

        _range_ = kwargs.pop('range', None)

        start = None
        count = None
        if _range_:
            if ':' in _range_:
                # page:size range
                (start, count) = map(lambda v: int(v), _range_.split(':'))
                start = (start - 1) * count

            elif '-' in _range_:
                # first-last range
                (start, count) = map(lambda v: int(v), _range_.split('-'))
                count = count - start + 1

            elif ',' in _range_:
                # first,count range
                (start, count) = map(lambda v: int(v), _range_.split(','))
            assert start >= 0 and count > 0, "Invalid range"

        signups = Signup.select().where(_where_).offset(start).limit(count).order_by(Signup.cdate).execute()
        for signup in signups:
            # converd cdate to datetime
            signup.cdate = datetime.strptime(signup.cdate, conf.datetime_store_format)

        return signups


    @classmethod
    def erase(cls, **kwargs):
        if 'id' in kwargs and kwargs['id']:
            return Signup.delete().where(Signup.id == kwargs['id']).execute()

    @classmethod
    def total(cls, **kwargs):
        return Signup.select().where(Signup._prepare_where_(**kwargs)).count()

    class Meta:
        database = db
        db_table = 'signups'

# for internal use
setattr(Signup, '_fields_', [field[0] for field in getmembers(Signup, lambda m: isinstance(m, Field))])

db.create_tables([Signup], safe=True)
db.commit()
