import sqlite3

from .queries import *

def init(db_file):
  return sqlite3.connect(db_file)

def close(db_con):
  db_conn.close()