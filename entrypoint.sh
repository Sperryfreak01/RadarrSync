#!/bin/ash

# Create /Config.txt based on the environment variables we were passed

cat << EOF > /Config.txt
[Radarr]
url = $SOURCE_RADARR_URL
key = $SOURCE_RADARR_KEY
path = $SOURCE_RADARR_PATH

[Radarr-target]
url = $TARGET_RADARR_URL
key = $TARGET_RADARR_KEY
path_from = $SOURCE_RADARR_PATH
path_to = $TARGET_RADARR_PATH
# Sync movies coming _from_ the source in this quality profile
profile = $SOURCE_RADARR_PROFILE_NUM
# When adding movise to the destination Radarr, use _this_ quality profile (may differ from source)
target_profile = $TARGET_RADARR_PROFILE_NUM
EOF

# Now execute the sync script in a loop, waiting DELAY before running again
while true
do
	python /RadarrSync.py 
	sleep $DELAY
done
