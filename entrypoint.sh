#!/bin/ash

# Create /Config.txt based on the environment variables we were passed

cat << EOF > /Config.txt
[Radarr]
url = $TARGET_RADARR_URL
key = $TARGET_RADARR_KEY

[Radarr4k]
url = $SOURCE_RADARR_URL
key = $SOURCE_RADARR_KEY
profile = $SOURCE_RADARR_PROFILE_NUM
EOF

# Now execute the sync script
python /RadarrSync.py 
