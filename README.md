# Introduction

I hate to loose fresh hot videos because of modern YT rules, so I download everything to watch offline later, and I'd like to read the comments too.

This repo contains massive YT comments downloader utility - screpper222.

It scans input path and tries to download comments for each found YT video. Specific video file naming is required: blablabla-youtubeID.webm or blablabla-youtubeID.mp4 etc.
Example of youtube ID is "dQw4w9WgXcQ". This ID is passed to youtube-comment-downloader tool, which produces a json file, if the video is not banned yet ;)

Screpper222 transforms comments from json dump into human-readable text file, and also updates its creation date by one from the video file.
If same video processed again, multiple versions of comment dumps are kept. So that comments being deleted could be found in earlier dump.

# Required tools

* youtube-dl or yt-dlp (later is faster) 
* youtube-comment-downloader [https://github.com/egbertbouman/youtube-comment-downloader]

# Usage

Typical usage is as follows:
1. Download videos with youtube-dl / yt-dlp. Quick example of how to download all Анатолий Шарий's videos, say in a E:/video_tmp/Sharij directory:
```
yt-dlp -r 3000k -f bestvideo+bestaudio --yes-playlist --download-archive downloaded.txt --no-post-overwrites --cookies youtube.com_cookies.txt -ci -a links.txt 
```
where -r is for limit speed, and "links.txt" is a file that has eiter particular videos or even the whole playlist single link:
```
# funny related video
https://youtu.be/BhaI2SqxHjE
# full playlist
https://www.youtube.com/user/SuperSharij/videos
```

2. Change destination path and options at the bottom of screpper222.py:
```
    paths = ['E:/video_tmp/Sharij']
    opts = {
         'min_new_comments': 500,  # min new comments to keep the new version of a dump.
         'min_new_comments_perc': 10,  # % of new comments to keep the new version of a dump.
         'skip_existing': True
    }
```
3. Execute
   python3 screpper222.py 
