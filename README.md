# Introduction

I hate to loose fresh hot videos because of modern YT rules, so I download everything to watch offline later, and I'd like to read hot comments too.
This repo contains my custom massive YT comments downloader which transforms comments from json into readable txt files.
Specific video file naming is required: blablabla-youtubeID.webm or blablabla-youtubeID.mp4 etc.
Example of youtubeID is "dQw4w9WgXcQ" and it is used for downloading comments with youtube-comment-downloader.

# Required software

* youtube-comment-downloader
* youtube-dl / yt-dlp (faster)

# Usage

Basic usage is:
1. Download new videos with 
1. Change destination path and options in the end of screpper222.py:
```
    paths = ['E:/video_tmp/Podolyaka']
    opts = {
         'min_new_comments': 500,  # min new comments to keep new version of dump. New dump is always added.
         'min_new_comments_perc': 10,  # % of new comments, to keep new dump
         'skip_existing': True
    }
```
3. Execute
   python3 screpper222.py 
