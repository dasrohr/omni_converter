''' SELECT DATA '''

def get_secret(db, *args):
  '''
  return the hashed password from a database for a given username
  return false if user does not exist
  '''
  cur = db.cursor()
  secret = cur.execute('SELECT secret FROM user WHERE username == ?', args).fetchone()
  if len(secret) < 1:
    return False
  return secret[0]

def check_id(db, *id):
  '''
  query for a given id
  return false if not exist
  returm ture if exists
  '''
  cur = db.cursor()
  result = cur.execute('SELECT id FROM history WHERE id == ?', id).fetchall()
  if len(result) < 1:
    return False
  return True


def get_filename(db, *id):
  '''
  query for a given id and get the filename
  return a touple with the filename and the path to it (only folders, no full filepath)
  '''
  cur = db.cursor()
  result = cur.execute('SELECT path, filename FROM files WHERE id == ?', id).fetchone()
  if not result:
    return False
  return result

def check_for_existing_link(db, id, path):
  '''
  chek if there is already a link to a file in the given Path
  this should prevent multiple links to a file in a single Path
  return True if there is already a link to the ID in the given Path
  return False if there is no link to the ID in the given Path
  '''
  cur = db.cursor()
  result = cur.execute('SELECT count() FROM files WHERE id == ? AND path == ? AND type == "l"', (id, path)).fetchone()[0]
  if result > 0:
    return True
  return False


''' INSERT DATA '''

def add_to_history(db, **kwargs):
  '''
  add data to the history database
  '''
  cur = db.cursor()
  print('DEBUG: {}'.format(kwargs))
  cur.execute('INSERT INTO history (id, source, date, playlist, url, source_title) VALUES (:id, :source, :date, :playlist, :url, :source_title)', kwargs)
  db.commit()

def add_file(db, **kwargs):
  '''
  add a file that has been loaded to the database
  '''
  cur = db.cursor()
  print('DEBUG: {}'.format(kwargs))
  cur.execute('INSERT INTO files VALUES (:id, :path, :filename, :art, :albart, :alb, :type, :target)', kwargs)
  db.commit()