# Urbane
OpenStack signup service

## Setup / Config

```
0. apt install python python-dev python-pip git python-setuptools
1. git clone urbane_repo
2. apt install libxml2-dev libxslt-dev zlib1g-dev
3. sudo pip install --upgrade -r requirements.txt
4. cd urbane
5. edit pecan configuration file `config.py`
6. edit urbane configuration file `urbane.conf`
7. run urbane service:
  sudo PYTHONPATH=`pwd` pecan serve config.py
8. add Urbane (signup) service endpoint into OpenStack Keystone (execute command on keystone host):
  openstack endpoint create --region RegionOne signup public http://$URBANE_HOST:6996
```
