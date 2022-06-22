# Introduction

I hate to loose fresh hot videos because of modern YT rules, so I download everything to watch offline later, and I'd like to read the comments too.

This repo contains massive YT comments downloader utility - screpper222.

It scans input path and tries to download comments for each found YT video. Specific video file naming is required: blablabla-youtubeID.webm or blablabla-youtubeID.mp4 etc.
Example of youtube ID is "dQw4w9WgXcQ". This ID is passed to youtube-comment-downloader tool, which produces a json file, if the video is not banned yet ;)

Screpper222 transforms comments from json dump into human-readable text file, and also updates its creation date by one from source video file. 
If same video processed again, multiple versions of comment dumps are kept (interesting comments are often deleted, but could be found in earlier dumps).

# Required tools

* youtube-dl or yt-dlp (later is faster) 
* youtube-comment-downloader [https://github.com/egbertbouman/youtube-comment-downloader]

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
