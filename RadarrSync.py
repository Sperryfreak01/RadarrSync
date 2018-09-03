import os
import logging
import requests
import json
import configparser
import sys


DEV = True

########################################################################################################################
logger = logging.getLogger()
logger.setLevel(logging.INFO)
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

# Create a session and ignore locally configured proxy settings
session = requests.Session()
session.trust_env = False

radarr4k_url = ConfigSectionMap("Radarr4k")['url']
radarr4k_key = ConfigSectionMap("Radarr4k")['key']
radarr4kMovies = session.get('{0}/api/movie?apikey={1}'.format(radarr4k_url, radarr4k_key))

radarr_url = ConfigSectionMap("Radarr")['url']
radarr_key = ConfigSectionMap("Radarr")['key']
radarrMovies = session.get('{0}/api/movie?apikey={1}'.format(radarr_url, radarr_key))

# Logs error responses from the server, usefull for trying to figure out no API calls
if radarrMovies.status_code != 200:
    logger.error('Radarr server error - response {}'.format(radarrMovies.status_code))
    sys.exit(0)
if radarr4kMovies.status_code != 200:
    logger.error('4K Radarr server error - response {}'.format(radarr4kMovies.status_code))
    sys.exit(0)


movieIds4k = []
for movie4k in radarr4kMovies.json():
    movieIds4k.append(movie4k['tmdbId'])
    #logger.debug('found movie to be added')

newMovies = 0
searchid = []
for movie in radarrMovies.json():
    if movie['profileId'] == 5:
        if movie['tmdbId'] not in movieIds4k:
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

            r = session.post('{0}/api/movie?apikey={1}'.format(radarr4k_url, radarr4k_key), data=json.dumps(payload))
            searchid.append(int(r.json()['id']))
            logger.info('adding {} to Radarr 4k server'.format(movie['title']))
        else:
            logging.debug('{0} already in 4k library'.format(movie['title']))


if len(searchid):
    payload = {'name' : 'MoviesSearch', 'movieIds' : searchid}
    session.post('{0}/api/command?apikey={1}'.format(radarr4k_url, radarr4k_key),data=json.dumps(payload))

