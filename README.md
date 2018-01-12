# Inststall Requirements
- pip install Celery Celery[redis] eyed3 Pillow unidecode validators
- apt insall redis celery
  - see Celery-Documentations for integration with systemd

# Files
 - omni_tasks.py  -> defines worker for Celery Queues
 - omni_httpd.py  -> spwans a httpd and performs basic url-check
 - res/           -> contains ressources for cover-generation
 - ytie/          -> java app - parses string and creates usefull 'artist - title' conventions
                  (written by dderjoel)
  
# ToDo
 - See Projects & Issues @ GIT
