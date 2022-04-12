import os
import logging
import subprocess
from time import sleep

max_load_retry = 30
sleep_init = 0.2
sleep_backstep = 1.5

tmp_file_path = ''

special_names_src = ['Seagate', 'system', 'windows', 'temp', 'tmp',
                     'ProgramData',
                     '..', '.', 'home', "Documents and Settings", 'games',
                     "Program Files (x86)", "Program Files", "Windows",
                     "System Volume Information", '$RECYCLE.BIN']
special_names = set()
for s in special_names_src:
    special_names.add(s.strip().upper())
logging.info('special dirs: %s', repr(special_names))

comments_dir = 'comments_yt'
yt_length = len('C5gtIXxo2Ws')
logging.info('yt_length: %d', yt_length)

dot_part_ext = ".part"

file_types = ["mkv", "mp4", 'webm', 'part']

total_files = 0
interesting_files = 0
subfolders = 0
created_comments = 0


def create_comments_if_missing(start_path):
    comments_path = os.path.join(start_path, comments_dir)
    if not os.path.exists(comments_path):
        logging.info('Creating dir %s', comments_path)
        os.mkdir(comments_path)
    return comments_path


def grep_ytid(f):
    dot_left_part = f[:f.rfind('.')]
    minus_right_parts = dot_left_part.split('-')
    minus_right_part = minus_right_parts[-1]
    k = 1
    while len(minus_right_part) < yt_length and len(minus_right_parts) > k:
        minus_right_part = minus_right_parts[-k - 1] + '-' + minus_right_part
        k += 1

    if len(minus_right_part) == yt_length:
        return minus_right_part

    return ''


def check_existing_comments(comments_path, n=1, prev=None, origin=None):
    if os.path.exists(comments_path):
        if origin is None:
            origin = comments_path
        base, ext = os.path.splitext(origin)
        new_path = base + '_' + str(n) + ext
        comments_path, prev = check_existing_comments(new_path, n + 1, comments_path, origin)
    return comments_path, prev


def get_lines_count(file_path):
    if file_path is None:
        return 0
    try:
        return int(subprocess.check_output(["wc", "-l", file_path]).decode("utf8").split()[0])
    except Exception:
        # иногда может не срабатывать из-за символов windows, которые запрещены в файлах linux
        # Используем стандартный подход:
        count = 0
        with open(file_path, 'r', errors="ignore") as fp:
            for _line in fp:
                count += 1
        return count


def del_file(file_path):
    if not file_path:
        return
    if os.path.exists(file_path):
        os.remove(file_path)


def process_video(f, ytid, comments_dir_path, opts):
    min_new_comments_to_keep = opts['min_new_comments']
    min_new_comments_to_keep_perc = opts['min_new_comments_perc'] / 100
    skip_existing = opts['skip_existing']
    logging.info('Loading comments for %s', f)

    comments_name, ext = os.path.splitext(f)

    # откусываем временное расширение .part
    if ext == dot_part_ext:
        comments_name = os.path.splitext(f)[0]
    comments_name += '.json'

    comments_path = os.path.join(comments_dir_path, comments_name)
    new_comments, prev_comments = check_existing_comments(comments_path)
    if skip_existing and prev_comments is not None:
        logging.info('Skip existing comments for %s', f)
        return

    global tmp_file_path
    tmp_file_path = new_comments
    cmd = ['youtube-comment-downloader', '--youtubeid=' + ytid, '--output', new_comments]
    logging.info(' '.join(cmd))

    try_load = 0
    sleep_secs = sleep_init
    while try_load != max_load_retry:
        result = subprocess.run(cmd)
        if result.returncode != 0:
            del_file(new_comments)
            logging.info('Sleep %d seconds after error', sleep_secs)
            sleep(sleep_secs)
            sleep_secs *= sleep_backstep
        else:
            break

    new_lines = get_lines_count(new_comments)
    logging.info('Got %d new_lines', new_lines)

    # Если размер 0 - удаляем
    if not new_lines:
        logging.info('DEL - no comments!')
        del_file(new_comments)
        return
    if prev_comments is not None:
        # или число коментов совпадает с предыдущим - удаляем
        old_lines = get_lines_count(prev_comments)
        if new_lines == old_lines:
            logging.info('DEL - Same amount of comments (%d)', new_lines)
            del_file(new_comments)
            return

        # Не нашли N новых комментов - удаляем
        if (min_new_comments_to_keep is not None and new_lines - old_lines < min_new_comments_to_keep) and \
                (min_new_comments_to_keep_perc is not None and old_lines > 0 and \
                 (new_lines - old_lines) / old_lines < min_new_comments_to_keep_perc):
            logging.info('DEL - Not enough new comments (%d): %d -> %d',
                         new_lines - old_lines, old_lines, new_lines)
            del_file(new_comments)
            return
        else:
            logging.info('APPEND new comments (%d): %d -> %d',
                         new_lines - old_lines, old_lines, new_lines)
            return
    logging.info('ADD new comments (%d)', new_lines)
    global created_comments
    created_comments += 1


def scan_folder(start_path, opts):
    logging.info('Scanning %s', start_path)
    comments_path = None
    for f in os.listdir(start_path):
        if f == comments_dir:
            continue

        # Фильтруем системные и просто нежелательные каталоги
        skip = False
        for special_name in special_names:
            if f.upper() == special_name:
                skip = True
        if skip:
            logging.info('Skip special dir: %s', f)
            continue

        fullpath = os.path.join(start_path, f)
        if os.path.isfile(fullpath):
            global total_files
            total_files += 1
            if f.split('.')[-1] in file_types:
                ytid = grep_ytid(f)
                if ytid:
                    logging.info('File: %s', f)
                    global interesting_files
                    interesting_files += 1
                    # создаем папку только если нашли файл, похожий на ролик YT
                    if comments_path is None:
                        comments_path = create_comments_if_missing(start_path)
                    process_video(f, ytid, comments_path, opts)
                    global tmp_file_path
                    tmp_file_path = ''
            else:
                pass
        elif os.path.isdir(fullpath):
            if f.startswith('.'):
                continue
            logging.info('Subdir: %s', f)
            global subfolders
            subfolders += 1
            scan_folder(fullpath, opts)


def setup_logging(log_filepath):
    logging.root.handlers = []
    logging.basicConfig(filename=log_filepath,
                        encoding='utf-8',
                        format='%(asctime)s: %(message)s',
                        level=logging.DEBUG,
                        datefmt='%Y-%m-%d %I:%M:%S')
    console = logging.StreamHandler()
    console.setLevel(logging.DEBUG)
    formatter = logging.Formatter('%(message)s')
    console.setFormatter(formatter)
    logging.getLogger("").addHandler(console)


def go_scan(start_path, opts):
    try:
        scan_folder(start_path, opts)
    except KeyboardInterrupt:
        logging.info('Interrupted!')
    except Exception as ex:
        logging.info('Error - %s!' % repr(ex), exc_info=1)

    if tmp_file_path:
        logging.info('Cleaning tmp file: %s', tmp_file_path)
        del_file(tmp_file_path)

    logging.info('Processed total files: %s', total_files)
    logging.info('interesting files: %s', interesting_files)
    logging.info('folders: %s', subfolders)
    logging.info('created new comment files: %s', created_comments)


if __name__ == '__main__':
    paths = ['E:/video_tmp/Podolyaka']
    for start_path in paths:
        setup_logging('scrape_runtime.log')
        opts = {
          'min_new_comments': 500,
          'min_new_comments_perc': 10,  # % новых комментов
          'skip_existing': True
        }
        go_scan(start_path, opts)
