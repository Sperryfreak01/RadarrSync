import os
import logging
import requests
import json
import configparser
import sys
from bs4 import BeautifulSoup

DEV = True
WHAT_IF = True

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

# uses a private api call to get the profile information may be broken one day
def validateProfile(root_url, api, profileName):
    with requests.Session() as session:
        session.trust_env = False
        headers = {
            'X-Api-Key': api,
            'Referer': '{0}/settings/profiles'.format(root_url)
        }
        profiles = session.get('http://192.168.2.4:9004/api/profile', headers=headers).json()
    try:
        profileNum = int(profileName)
    #if isinstance(profileName, int):  # check and see if were given the profile number or the profle name
        if profileNum in range(1, len(profiles)+1):
            logger.debug('user supplied profile number ({0}) found on server'.format(profileName))
            return profileNum  # profile existsso return the ID to be consistant with value returned when a profile name supplied
        else:
            logger.warning('user supplied profile number ({0}) not found on server'.format(profileName))
            return False
    except:
    #else:
        for i in range(0, len(profiles)):
            if profiles[i]['name'] == profileName:
                logger.debug('{0} is profile {1}'.format(profiles[i]['name'], i + 1))
                return i + 1  # validated the profile is on the server so return the ID number
    logger.warning('user supplied profile name ({0}) not found on server'.format(profileName))
    return False  # Terrible catch all statement, didn't find the profile any other way


# @todo save profiles to config
# @body write the list of profiles back to the config file or add a command argument so people can check them
# listProfiles(SyncServer_url, SyncServer_key)  # gets a list of profiles from the server
# uses a private api call to get the profile information may be broken one day
def listProfiles(root_url, api):
    profileList = []
    with requests.Session() as session:
        session.trust_env = False
        headers = {
            'X-Api-Key': api,
             'Referer': '{0}/settings/profiles'.format(root_url)
        }
        profiles = session.get('{0}/api/profile'.format(root_url), headers=headers).json()
        for i in range(0, len(profiles)):
            logger.debug('{0} is profile {1}'.format(profiles[i]['name'], i+1))
            profileList.append({i+1: profiles[i]['name']})
    print(profileList)
    return profileList


# ---------------------------------------------Main Script-------------------------------------------------------------#

Config = configparser.ConfigParser()

# Loads an alternate config file so that I can work on my servers without uploading my personal config to github
if DEV:
    settingsFilename = os.path.join(os.getcwd(), 'Dev'
                                                 'Config.txt')
else:
    settingsFilename = os.path.join(os.getcwd(), 'Config.txt')
Config.read(settingsFilename)

# Build primary server URLs and retrieve a json object of the primary server movies
radarr_url = ConfigSectionMap("Radarr")['url']
radarr_key = ConfigSectionMap("Radarr")['key']
radarrSession = requests.Session()
radarrSession.trust_env = False
radarrMovies = radarrSession.get('{0}/api/movie?apikey={1}'.format(radarr_url, radarr_key))
if radarrMovies.status_code != 200:
    logger.error('Radarr server error - response {}'.format(radarrMovies.status_code))
    sys.exit(0)


# MultiServer support, iterates through the config file syncing to multiple radarr servers STILL A ONE WAY SYNC
for server in Config.sections():

    if server == 'Default' or server == "Radarr":
        continue  # Default/primary server section handled previously as it always needed so break out of the loop

    else:
        logger.debug('syncing to {0}'.format(server))
        session = requests.Session()
        session.trust_env = False
        SyncServer_url = ConfigSectionMap(server)['url']
        SyncServer_key = ConfigSectionMap(server)['key']
        SyncServer_profile = validateProfile(SyncServer_url, SyncServer_key, ConfigSectionMap(server)['profile'])
        SyncServerMovies = session.get('{0}/api/movie?apikey={1}'.format(SyncServer_url, SyncServer_key))
        if SyncServerMovies.status_code != 200:
            logger.error('4K Radarr server error - response {}'.format(SyncServerMovies.status_code))
            sys.exit(0)

        if WHAT_IF:
            continue


    # build a list of movied IDs already in the sync server, this is used later to prevent readding a movie that already
    # exists.
    # TODO refactor variable names to make it clear this builds list of existing not list of movies to add
    # TODO #11 Add reconciliation of sync server to primary server
    movieIds_to_syncserver = []
    for movie_to_sync in SyncServerMovies.json():
        movieIds_to_syncserver.append(movie_to_sync['tmdbId'])
        #logger.debug('found movie to be added')

    newMovies = 0
    searchid = []
    for movie in radarrMovies.json():
        if movie['profileId'] == SyncServer_profile:
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

