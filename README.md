# RadarrSync
Syncs two Radarr servers through web API.  

### Why
Many Plex servers choke if you try to transcode 4K files. To address this a common approach is to keep a 4k and a 1080/720 version in seperate libraries.

Radarr does not support saving files to different folder roots for different quality profiles.  To save 4K files to a seperate library in plex you must run two Radarr servers.  This script looks for movies with a quality setting of 4k on one server and creates the movies on a second server.  


### Configuration
 1. Edit the Config.txt file and enter your servers URLs and API keys for each server.  

    Example Config.txt:
    ```ini
    [Radarr]
    url = https://example.com:443
    key = FCKGW-RHQQ2-YXRKT-8TG6W-2B7Q8
    
    [Radarr4k]
    url = http://127.0.0.1:8080
    key = FCKGW-RHQQ2-YXRKT-8TG6W-2B7Q8
    ```
 2. Edit 4K profile on the server that will download 1080/720p files.  You want the quality profile to download the highest non-4k quality your Plex server can stream with choking. 


#### How to Run
Recomended to run using cron every 15 minutes or an interval of your preference.
```bash
python RadarSync.py
```


#### Requirements
 * Python 3.4 or greater
 * 2x Radarr servers
 * Install requirements.txt

#### Notes
 * Ensure that the root path is the same on both servers. ie /movies
 
 
 
