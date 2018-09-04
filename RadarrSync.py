import os
import logging
import requests
import json
import configparser
import sys


DEV = False

########################################################################################################################
logger = logging.getLogger()
logger.setLevel(logging.DEBUG)
logFormatter = logging.Formatter("%(asctime)s [%(threadName)-12.12s] [%(levelname)-5.5s]  %(message)s")

fileHandler = logging.FileHandler("./Output.txt")
fileHandler.setFormatter(logFormatter)
logger.addHandler(fileHandler)

consoleHandler = logging.StreamHandler(sys.stdout)
consoleHandler.setFormatter(logFormatter)
logger.addHandler(consoleHandler)
########################################################################################################################


def ConfigSectionMap(section):
    dict1 = {}
    options = Config.options(section)
    for option in options:
        try:
            dict1[option] = Config.get(section, option)
            if dict1[option] == -1:
                logger.debug("skip: %s" % option)
        except:
            print("exception on %s!" % option)
            dict1[option] = None
    return dict1


Config = configparser.ConfigParser()

# Loads an alternate config file so that I can work on my servers without uploading config to github
if DEV:
    settingsFilename = os.path.join(os.getcwd(), 'Dev'
                                                 'Config.txt')
else:
    settingsFilename = os.path.join(os.getcwd(), 'Config.txt')
Config.read(settingsFilename)

radarr_url = ConfigSectionMap("Radarr")['url']
radarr_key = ConfigSectionMap("Radarr")['key']
radarrSession = requests.Session()
radarrSession.trust_env = False
radarrMovies = radarrSession.get('{0}/api/movie?apikey={1}'.format(radarr_url, radarr_key))
if radarrMovies.status_code != 200:
    logger.error('Radarr server error - response {}'.format(radarrMovies.status_code))
    sys.exit(0)

for server in Config.sections():

    if server == 'Default' or server == "Radarr":
        continue  # Default section handled previously as it always needed

    else:
        logger.debug('syncing to {0}'.format(server))

        session = requests.Session()
        session.trust_env = False
        SyncServer_url = ConfigSectionMap(server)['url']
        SyncServer_key = ConfigSectionMap(server)['key']
        SyncServerMovies = session.get('{0}/api/movie?apikey={1}'.format(SyncServer_url, SyncServer_key))
        if SyncServerMovies.status_code != 200:
            logger.error('4K Radarr server error - response {}'.format(SyncServerMovies.status_code))
            sys.exit(0)

    # build a list of movied IDs already in the sync server, this is used later to prevent readding a movie that already
    # exists.
    # TODO refactor variable names to make it clear this builds list of existing not list of movies to add
    # TODO add reconcilliation to remove movies that have been deleted from source server
    movieIds_to_syncserver = []
    for movie_to_sync in SyncServerMovies.json():
        movieIds_to_syncserver.append(movie_to_sync['tmdbId'])
        #logger.debug('found movie to be added')

    newMovies = 0
    searchid = []
    for movie in radarrMovies.json():
        if movie['profileId'] == int(ConfigSectionMap(server)['profile']):
            if movie['tmdbId'] not in movieIds_to_syncserver:
                logging.debug('title: {0}'.format(movie['title']))
                logging.debug('qualityProfileId: {0}'.format(movie['qualityProfileId']))
                logging.debug('titleSlug: {0}'.format(movie['titleSlug']))
                images = movie['images']
                for image in images:
                    image['url'] = '{0}{1}'.format(radarr_url, image['url'])
                    logging.debug(image['url'])
                logging.debug('tmdbId: {0}'.format(movie['tmdbId']))
                logging.debug('path: {0}'.format(movie['path']))
                logging.debug('monitored: {0}'.format(movie['monitored']))

                payload = {'title': movie['title'],
                           'qualityProfileId': movie['qualityProfileId'],
                           'titleSlug': movie['titleSlug'],
                           'tmdbId': movie['tmdbId'],
                           'path': movie['path'],
                           'monitored': movie['monitored'],
                           'images': images,
                           'profileId': movie['profileId'],
                           'minimumAvailability': 'released'
                           }

                r = session.post('{0}/api/movie?apikey={1}'.format(SyncServer_url, SyncServer_key), data=json.dumps(payload))
                searchid.append(int(r.json()['id']))
                logger.info('adding {0} to {1} server'.format(movie['title'], server))
            else:
                logging.debug('{0} already in {1} library'.format(movie['title'], server))


    if len(searchid):
        payload = {'name' : 'MoviesSearch', 'movieIds' : searchid}
        session.post('{0}/api/command?apikey={1}'.format(SyncServer_url, SyncServer_key), data=json.dumps(payload))

