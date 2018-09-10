import os
import logging
import requests
import json
import configparser
import sys
from bs4 import BeautifulSoup

DEV = True # If your are not Sperryfreak01 this should be False

# TODO add way for users to see what would sync without syncing
# @body I think the best way would be to create a sync report "Sync_Test.txt" or something like it
WHAT_IF = True
Config = configparser.ConfigParser()


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
        if profileNum in range(1, len(profiles)+1):
            logger.debug('user supplied profile number ({0}) found on server'.format(profileName))
            return profileNum  # profile exists so return the ID to be consistant with value returned when a profile name supplied
        else:
            logger.warning('user supplied profile number ({0}) not found on server'.format(profileName))
            return False
    except:
        for i in range(0, len(profiles)):
            if profiles[i]['name'].lower() == profileName.lower():
                logger.debug('{0} is profile {1}'.format(profiles[i]['name'], i + 1))
                return i + 1  # validated the profile is on the server so return the ID number
    logger.warning('user supplied profile name ({0}) not found on server'.format(profileName))
    return False  # Terrible catch all statement, didn't find the profile any other way


# @todo save profiles to config
# @body write the list of profiles back to the config file or add a command argument so people can check them
# listProfiles(syncServer['url'], syncServer['key'])  # gets a list of profiles from the server
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


def addMovie(primaryServer, syncServer):
    newMovies = 0
    searchid = []
    for movie in primaryServer['movies']:  # interate through primary server, building a list of movies w/ correct profile
        if movie['profileId'] == syncServer['profile']:
            if movie['tmdbId'] not in syncServer['movies']:  # make sure we dont re-add movies that are already there
                images = movie['images']  # Images required to create movie, pull URL from primary server
                logging.debug('''
                                    Title: {0}
                                    QualityProfileId: {1}
                                    TitleSlug: {2}
                                    TmdbId: {3}
                                    Path: {4}
                                    Monitored: {5}
                                    '''.format(movie['title'],
                                               movie['qualityProfileId'],
                                               movie['titleSlug'],
                                               movie['tmdbId'],
                                               movie['path'],
                                               movie['monitored']
                                               )
                              )
                for image in images:
                    image['url'] = '{0}{1}'.format(primaryServer['url'], image['url'])
                    logging.debug(image['url'])

                payload = {'title': movie['title'],  # build the submission to create the movie on the SyncServer
                           'qualityProfileId': movie['qualityProfileId'],
                           'titleSlug': movie['titleSlug'],
                           'tmdbId': movie['tmdbId'],
                           'path': movie['path'],  # TODO Consider adding support for user paths in config file
                           'monitored': movie['monitored'],
                           'images': images,
                           'profileId': movie['profileId'],
                           'minimumAvailability': 'released'
                           }
                addMovie = syncServer['session'].post('{0}/api/movie?apikey={1}'.format(syncServer['url'],
                                                                          syncServer['key']
                                                                          ),
                                        data=json.dumps(payload)
                                        )
                if addMovie.status_code != 201:
                    logger.error('Failed to add move to {0} - response {1} - {2}'.format(syncServer['name'],
                                                                                         addMovie.status_code,
                                                                                         addMovie.text
                                                                                         )
                                 )
                    continue
                else:
                    searchid.append(int(addMovie.json()['id']))
                    logger.info('added {0} to {1} server'.format(movie['title'], syncServer['name']))
            else:
                logging.debug('{0} already in {1} library'.format(movie['title'], syncServer['name']))
        else:
            logging.debug('Skipping {0}, wanted profile: {2} found profile: {1}'.format(movie['title'],
                                                                                        movie['profileId'],
                                                                                        syncServer['profile']
                                                                                        )
                          )
    if len(searchid):
        payload = {'name': 'MoviesSearch', 'movieIds': searchid}
        syncServer['session'].post('{0}/api/command?apikey={1}'.format(syncServer['url'],
                                                         syncServer['key']
                                                         ),
                     data=json.dumps(payload)
                     )


def delMovie(primaryServer, syncServer):
    for movieid in syncServer['movieIDs']:  # go through all the tmdb IDs on the sync server
        if movieid not in primaryServer['movieIDs']:  # If the ID is not found on the primary server then we del from sync
            for movie in syncServer['movies']:  # Need to find the radarr ID from the tmdb ID
                if movie['tmdbId'] == movieid:
                    logger.debug('{0} was found on {1} but not on the primary server'.format(movie['id'],
                                                                                             syncServer['name']
                                                                                             )
                                 )
                    delMovie = syncServer['session'].delete('{0}/api/movie/{2}?apikey={1}'.format(syncServer['url'],
                                                                                                  syncServer['key'],
                                                                                                  movie['id']
                                                                                                  )
                                                            )
                    if delMovie.status_code != 200:
                        logger.error('Failed to delete move to {0} - response {1} - {2}'.format(syncServer['name'],
                                                                                                delMovie.status_code,
                                                                                                delMovie.text
                                                                                             )
                                     )
                        continue
                    else:
                        logger.info('removed {0} on {1} server'.format(movie['title'],
                                                                       syncServer['name']
                                                                       )
                                    )


# ---------------------------------------------Main Script-------------------------------------------------------------#
# Loads an alternate config file so that I can work on my servers without uploading my personal config to github
if DEV:
    settingsFilename = os.path.join(os.getcwd(), 'Dev'
                                                 'Config.txt')
else:
    settingsFilename = os.path.join(os.getcwd(), 'Config.txt')
Config.read(settingsFilename)

# Dynamically configure the logging level based on the user settings in the config
logger = logging.getLogger()
try:
    logLevel = ConfigSectionMap("General")['loglevel']
    print(logLevel)
    if logLevel.upper() == 'INFO':
        logger.setLevel(logging.INFO)
    elif logLevel.upper() == 'DEBUG':
        logger.setLevel(logging.DEBUG)
        logger.debug('logging debug info')
    elif logLevel.upper() == 'WARN':
        logger.setLevel(logging.WARNING)
    else:
        logger.setLevel(logging.INFO)
except:
    logger.setLevel(logging.INFO)
logFormatter = logging.Formatter("%(asctime)s [%(threadName)-12.12s] [%(levelname)-5.5s]  %(message)s")

fileHandler = logging.FileHandler("./Output.txt")
fileHandler.setFormatter(logFormatter)
logger.addHandler(fileHandler)

consoleHandler = logging.StreamHandler(sys.stdout)
consoleHandler.setFormatter(logFormatter)
logger.addHandler(consoleHandler)

# Build primary server URLs and retrieve a json object of the primary server movies
radarrServer = {}
radarrServer['url'] = ConfigSectionMap("Radarr")['url']
radarrServer['key'] = ConfigSectionMap("Radarr")['key']
radarrServer['session'] = requests.Session()
radarrServer['session'].trust_env = False
radarrMovies = radarrServer['session'].get('{0}/api/movie?apikey={1}'.format(radarrServer['url'], radarrServer['key']))
if radarrMovies.status_code != 200:
    logger.error('Radarr server error - response {}'.format(radarrMovies.status_code))
    sys.exit(0)

radarrServer['movies'] = radarrMovies.json()
radarrServer['movieIDs'] = []
for libraryMovie in radarrMovies.json():
    radarrServer['movieIDs'].append(libraryMovie['tmdbId'])

# MultiServer support, iterates through the config file syncing to multiple radarr servers STILL A ONE WAY SYNC
for server in Config.sections():
    syncServer = {}
    if server == 'Default' or server == "Radarr" or server == "General":
        continue  # Default/primary server section handled previously as it always needed so break out of the loop
    else:
        logger.debug('syncing to {0}'.format(server))
        syncServer['name'] = server
        syncServer['session'] = requests.Session()
        syncServer['session'].trust_env = False
        syncServer['url'] = ConfigSectionMap(syncServer['name'])['url']
        syncServer['key'] = ConfigSectionMap(syncServer['name'])['key']
        syncServer['profile'] = validateProfile(syncServer['url'], syncServer['key'], ConfigSectionMap(server)['profile'])
        if not syncServer['profile']:
            logger.error('The profile provided was not found on {}'.format(syncServer['name']))
            continue
        SyncServerMovies = syncServer['session'].get('{0}/api/movie?apikey={1}'.format(syncServer['url'], syncServer['key']))
        if SyncServerMovies.status_code != 200:
            logger.error('4K Radarr server error - response {}'.format(SyncServerMovies.status_code))
            sys.exit(0)

    # build a list of movied IDs already in the sync server, used later to prevent readding a movie that already exists.
    syncServer['movies'] = SyncServerMovies.json()
    syncServer['movieIDs'] = []
    for libraryMovie in SyncServerMovies.json():
        syncServer['movieIDs'].append(libraryMovie['tmdbId'])

    addMovie(radarrServer, syncServer)

    try:
        bidirectional = ConfigSectionMap('General')['bidirectional_sync']
        if bidirectional.lower() == 'enabled':
            delMovie(radarrServer, syncServer)
    except KeyError:
        bidirectional = 'false'


