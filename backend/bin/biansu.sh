#!/bin/bash

export PATH=/Library/Frameworks/Python.framework/Versions/3.12/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin
export IMAGEIO_FFMPEG_EXE=/Users/peterzhang/Documents/ffmpeg/ffmpeg

echo "==== $(date) START ====" >> /Users/peterzhang/scripts/video-tempo-studio/backend/biansu.log

/Library/Frameworks/Python.framework/Versions/3.12/bin/python3 /Users/peterzhang/scripts/video-tempo-studio/backend/apps/video_processor.py --directory "/Users/peterzhang/Dropbox/视频变速自动化" >> /Users/peterzhang/scripts/video-tempo-studio/backend/biansu.log 2>&1

echo "==== $(date) END ====" >> /Users/peterzhang/scripts/video-tempo-studio/backend/biansu.log
