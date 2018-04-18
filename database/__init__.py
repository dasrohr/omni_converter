import sqlite3

from .queries import *

def initialize_db(db_file):
  '''
  Initialize a new Database-File
  statements will fail when there is already a db file, containing those tables
  should only be executed when db-file does not exist anyway
  note that the Tables are empty, there is no defualt User.
  A User needs to be added manually after initialisation for BasicAuth to work
  '''
  from os import path
  if path.isfile(db_file):
    print('{} alreaedy exist'.format(db_file))
    return False

  db = sqlite3.connect(db_file)
  cur = db.cursor()

sql_statements = ['CREATE TABLE "files" ( "id" TEXT NOT NULL, "path" TEXT NOT NULL, "filename" TEXT NOT NULL UNIQUE, "art" TEXT NOT NULL, "albart" TEXT NOT NULL, "alb" TEXT NOT NULL, "title" TEXT NOT NULL, "type" TEXT NOT NULL, "target" TEXT DEFAULT NULL, "date" TEXT NOT NULL, PRIMARY KEY(filename))', 'CREATE TABLE "history" ( "id" TEXT NOT NULL UNIQUE, "source" TEXT NOT NULL, "date" TEXT NOT NULL, "playlist" TEXT DEFAULT NULL, "playlist_id" TEXT DEFAULT NULL, "url" TEXT NOT NULL, "source_title" TEXT NOT NULL, PRIMARY KEY(id))', 'CREATE TABLE "user" ( "username" TEXT NOT NULL UNIQUE, "secret" TEXT NOT NULL, PRIMARY KEY(username))']
  # execute defined statements from above
  for statement in sql_statements:
    cur.execute(statement)

  db.commit()
  db.close()


def connect(db_file):
  return sqlite3.connect(db_file)

def close(db_con):
  db_conn.close()
