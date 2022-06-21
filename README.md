# Introduction

I hate to loose fresh hot videos because of modern YT rules, so I download everything to watch offline later, and I'd like to read hot comments too.

This repo contains my custom massive YT comments downloader. It scans input path and tries to download comments for each found YT video. Specific video file naming is required: blablabla-youtubeID.webm or blablabla-youtubeID.mp4 etc.
Example of youtubeID is "dQw4w9WgXcQ". These IDs are passed to youtube-comment-downloader, and the tool produces a json file, if video is not banned yet.
Python utility transforms comments from json into readable text file, and also updates its creation date by date from source YT video file.

# Required tools

* youtube-dl / yt-dlp (faster)
* youtube-comment-downloader

# Usage

Basic usage is:
1. Download videos with youtube-dl / yt-dlp.
2. Change destination path and options in the end of screpper222.py:
```
    paths = ['E:/video_tmp/Podolyaka']
    opts = {
         'min_new_comments': 500,  # min new comments to keep new version of dump. New dump is always added.
         'min_new_comments_perc': 10,  # % of new comments, to keep new version of dump.
         'skip_existing': True
    }
```
3. Execute
   python3 screpper222.py 
