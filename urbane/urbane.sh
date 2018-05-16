#!/bin/sh

BASEDIR=`dirname $0`

cd $BASEDIR

PYTHONPATH=`pwd` pecan serve --reload config.py
