import json
import os
import logging
import subprocess
import sys
from datetime import datetime
from collections import defaultdict, OrderedDict
from time import sleep

max_load_retry = 0
extra_opt_retry = 7
sleep_init_seconds = 5
sleep_backstep = 1.1
skip_until = ''  # part of filename to skip processing.

tmp_file_path = ''
FORCE_EXIT = False

except_patterns_src = ['.f312.', '.f313.',
                       '.f247.', '.f248.',
                       '.f302.', '.f303.']
except_patterns = set()
for s in except_patterns_src:
    except_patterns.add(s.strip())

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

file_types = ["mkv", "mp4", 'webm', 'part', 'dummy']

total_files = 0
interesting_files = 0
subfolders = 0
created_comments = 0


def create_comments_dir_if_missing(start_path):
    comments_path = os.path.join(start_path, comments_dir)
    if not os.path.exists(comments_path):
        logging.info('Creating dir %s', comments_path)
        os.mkdir(comments_path)
    return comments_path


def grep_ytid(f: str):
    if '[' in f and ']' in f:
        ytid = f[f.find('[') + 1: f.find(']')]
        logging.info('%s -> ytid: %s', f, ytid)
        if len(ytid) == yt_length:
            logging.info('ytid is ok')
            return ytid

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


# (C) https://stackoverflow.com/a/68385697/17380035
def buf_count_newlines_gen(fname):
    def _make_gen(reader):
        while True:
            b = reader(2 ** 16)
            if not b:
                break
            yield b

    with open(fname, "rb") as f:
        count = sum(buf.count(b"\n") for buf in _make_gen(f.raw.read))
    return count


def get_lines_count(file_path):
    if file_path is None:
        return 0
    # return int(subprocess.check_output(["wc", "-l", file_path]).decode("utf8").split()[0])
    # wc -l может не срабатывать из-за символов windows, которые запрещены в файлах linux
    # Стандартный подход тоже глючит с ошибкой Error: failed to set sorting.
    #     count = 0
    #     with open(file_path, 'r', errors="ignore") as fp:
    #         for _line in fp:
    #             count += 1
    #     return count
    # Поэтому используем подход с бинарным чтением:
    return buf_count_newlines_gen(file_path)


def del_file(file_path):
    if not file_path:
        return
    if os.path.exists(file_path):
        os.remove(file_path)


def fmt_as_text(text, time, author):
    return '[%s, %s]: %s' % (author, time, text)


def set_file_mtime(new_path, opts, forced_mtime=False):
    if forced_mtime:
        if not 'forced_mtime' in opts or not opts['forced_mtime']:
            return

    if 'mtime' in opts:
        mtime = opts['mtime']
        try:
            os.utime(new_path, (mtime, mtime))
        except Exception as exc:
            logging.error('Cannot set mtime: %s', exc)


def convert_to_text(comments_path, opts):
    """
    Example:
    {"cid": "UgzNyqxPkw0q1ItcCKx4AaABAg", "text": "Шеф :elbowcough: всё пропало! гипс снимают! клиент уезжает!:yougotthis:",
    "time": "2 недели назад", "author": "сабурский атаман", "channel": "UCE9a7q_G99z6nqKlLxlIWdA", "votes": "1",
    "photo": "https://yt3.ggpht.com/ytc/AKedOLR00-5SL32nbcPq1Hr4D_s4--sC8Icoohjeqw=s176-c-k-c0x00ffffff-no-rj",
    "heart": false, "time_parsed": 1647356834.670765}

    {"cid": "UgyRRImNrOZVnb6Mn3Z4AaABAg", "text": "Живий тэхники)))",
    "time": "2 недели назад", "author": "Zhenia Savchik", "channel": "UCadMViBDkgfQTH7TrLbFcIg", "votes": "0",
    "photo": "https://yt3.ggpht.com/ytc/AKedOLSlusACjf3b75OBclluEG_Y7nBSDy4iJw_dLw=s176-c-k-c0x00ffffff-no-rj",
    "heart": false, "time_parsed": 1647356834.672717}
    """
    if not opts['convert_to_text']:
        return
    if not os.path.exists(comments_path):
        return

    if 'mark_text' in opts and opts['mark_text']:
        mark_text = opts['mark_text']
    else:
        mark_text = ''

    base, ext = os.path.splitext(comments_path)
    new_path = base + '.txt'
    mark_path = base + '.mark'
    if os.path.exists(new_path):
        set_file_mtime(new_path, opts, forced_mtime=True)
        return
    try:
        try:
            with open(mark_path, 'w+', encoding='utf-8') as of_mark:
                mark_timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                print(mark_timestamp, file=of_mark)
                print(mark_text, file=of_mark)
        except Exception as ext:
            print(ext)
            sys.exit(1)

        with open(comments_path, 'r', errors="ignore", encoding='utf-8') as fp, \
                open(new_path, 'w+', encoding='utf-8') as ofp:
            lines = fp.readlines()
            answers = defaultdict(list)
            jsons = map(lambda line: json.loads(line), lines)
            rows = OrderedDict()

            for j in jsons:
                cid = j['cid']
                text = j['text']
                time = j['time']
                author = j['author']
                formatted = fmt_as_text(text, time, author)
                if cid.find('.') >= 0:
                    pcid = cid[:cid.find('.')]
                    answers[pcid].append(formatted)
                else:
                    rows[cid] = formatted

            for cid, formatted in rows.items():
                print(formatted, file=ofp)
                if cid in answers:
                    for answer in answers[cid]:
                        print('  \\' + answer, file=ofp)
        set_file_mtime(new_path, opts)
        new_path = ''

    except KeyboardInterrupt:
        logging.info('Interrupted!')
    except Exception as ex:
        logging.info('Error converting to text: %s', repr(ex), exc_info=1)
    if new_path:
        logging.info('Cleaning tmp file: %s', new_path)
        del_file(new_path)


def check_existing_comments(comments_path, opts, n=1, prev=None, origin=None):
    if os.path.exists(comments_path):
        set_file_mtime(comments_path, opts, forced_mtime=True)
        opts['mark_text'] = 'UPDATE txt by existing json'
        convert_to_text(comments_path, opts)

        if origin is None:
            origin = comments_path
        base, ext = os.path.splitext(origin)
        new_path = base + '_' + str(n) + ext
        comments_path, prev = check_existing_comments(new_path, opts, n + 1, comments_path, origin)
    return comments_path, prev


def process_video(f, ytid, comments_dir_path, opts):
    global skip_until
    update_if_negative = opts['update_if_negative']
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
    new_comments_path, prev_comments_path = check_existing_comments(comments_path, opts)
    if skip_existing and prev_comments_path is not None:
        logging.info('Skip existing comments for %s', f)
        return

    if skip_until:
        if skip_until in new_comments_path:
            logging.info('Target file reached: %s', f)
            skip_until = ''
        else:
            logging.info('Skip for %s until %s', f, skip_until)
            return

    global tmp_file_path
    tmp_file_path = new_comments_path
    cmd = ['youtube-comment-downloader', '--youtubeid=' + ytid, '--output', new_comments_path]
    logging.info(' '.join(cmd))

    retry_count = 0
    sleep_secs = sleep_init_seconds
    while True:
        result = subprocess.run(cmd)
        if result.returncode == 0:
            break
        if retry_count == extra_opt_retry:
            sorting_issue = 'https://github.com/egbertbouman/youtube-comment-downloader/issues/105'
            sorting_fix_opt = '--sort=0'
            logging.warning('Append sorting fix option %s to bypass issue %s', sorting_fix_opt, sorting_issue)
            cmd.append(sorting_fix_opt)

        cmd_str = ' '.join(cmd)
        logging.error('Command failed:\n%s', cmd_str)
        del_file(new_comments_path)
        logging.info('Sleep %d seconds after retry (%s)', sleep_secs, retry_count)
        sleep(sleep_secs)
        sleep_secs *= sleep_backstep
        retry_count += 1
        if retry_count >= max_load_retry:
            return None
    set_file_mtime(new_comments_path, opts)
    new_lines = get_lines_count(new_comments_path)
    logging.info('Got %d new_lines', new_lines)

    # Если размер 0 - удаляем
    if not new_lines:
        logging.info('DEL - no comments!')
        del_file(new_comments_path)
        return None
    if prev_comments_path is not None:
        # или число коментов совпадает с предыдущим - удаляем
        old_lines = get_lines_count(prev_comments_path)
        if new_lines == old_lines:
            logging.info('DEL - Same amount of comments (%d)', new_lines)
            del_file(new_comments_path)
            return None

        if update_if_negative and new_lines <= old_lines - update_if_negative:
            logging.info('REMOVED %d comments: %d -> %d',
                         old_lines - new_lines, old_lines, new_lines)
            return new_comments_path

        # Не нашли N новых комментов - удаляем
        if (min_new_comments_to_keep is not None and new_lines - old_lines < min_new_comments_to_keep) and \
                (min_new_comments_to_keep_perc is not None and old_lines > 0 and \
                 (new_lines - old_lines) / old_lines < min_new_comments_to_keep_perc):
            logging.info('DEL - Not enough new comments (%d): %d -> %d',
                         new_lines - old_lines, old_lines, new_lines)
            del_file(new_comments_path)
            return None
        else:
            mark_text = f'APPEND new comments ({new_lines - old_lines}): {old_lines} -> {new_lines}'
            logging.info(mark_text)
            opts['mark_text'] = mark_text
            return new_comments_path
    mark_text = f'ADD new comments ({new_lines})'
    logging.info(mark_text)
    opts['mark_text'] = mark_text
    return new_comments_path


def scan_folder(start_path, opts):
    logging.info('Scanning %s', start_path)
    comments_path = None
    try:
        order_by_date = int(opts['order_by_date'])
    except KeyError:
        order_by_date = -1

    files = os.listdir(start_path)
    if order_by_date == -1:
        files.sort(key=lambda f: -os.path.getmtime(os.path.join(start_path, f)))
    elif order_by_date == 1:
        files.sort(key=lambda f: os.path.getmtime(os.path.join(start_path, f)))
    for fcount, f in enumerate(files):
        if f == comments_dir:
            continue

        # Фильтруем системные и просто нежелательные каталоги
        skip = False
        for special_name in special_names:
            if f.upper() == special_name:
                skip = True
                break
        if skip:
            logging.info('Skip technical dir: %s', f)
            continue

        for except_pattern in except_patterns:
            if except_pattern in f:
                skip = True
                break
        if skip:
            logging.info('Skip technical file with %s: %s', except_pattern, f)
            continue

        fullpath = os.path.join(start_path, f)
        if os.path.isfile(fullpath):
            global total_files
            total_files += 1
            if f.split('.')[-1] in file_types:
                ytid = grep_ytid(f)
                if ytid:
                    logging.info('File: %s (%d of %d, %.1f %%)', f, fcount, len(files),
                                 100 * fcount / len(files))
                    global interesting_files
                    interesting_files += 1

                    # mtime is not UTC, but local time
                    mtime = os.path.getmtime(fullpath)
                    opts['mtime'] = mtime
                    logging.info('Date: %s', datetime.fromtimestamp(mtime))

                    # создаем папку только если нашли файл, похожий на ролик YT
                    if comments_path is None:
                        comments_path = create_comments_dir_if_missing(start_path)

                    opts['mark_text'] = ''  # clean mark text
                    result_comments_path = process_video(f, ytid, comments_path, opts)
                    if result_comments_path:
                        global created_comments
                        created_comments += 1
                        convert_to_text(result_comments_path, opts)

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
    global skip_until, FORCE_EXIT
    if FORCE_EXIT:
        return

    skip_until = opts['skip_until'] if 'skip_until' in opts else ''
    try:
        scan_folder(start_path, opts)
    except KeyboardInterrupt:
        FORCE_EXIT = True
        logging.info('Interrupted!')
    except Exception as ex:
        logging.info('Error - %s!' % repr(ex), exc_info=1)

    if tmp_file_path:
        logging.info('Cleaning tmp file: %s', tmp_file_path)
        del_file(tmp_file_path)

    logging.info('Completed path %s', start_path)
    logging.info('Processed total files: %s', total_files)
    logging.info('interesting files: %s', interesting_files)
    logging.info('folders: %s', subfolders)
    logging.info('created new comment files: %s', created_comments)


if __name__ == '__main__':
    setup_logging('scrape_runtime2.log')
    paths = ['H:/']
    # paths = ['H:/polit2022/Ukraine war/8 канал/fresh']
    for start_path in paths:
        setup_logging('scrape_runtime2.log')
        opts = {
            # 0 - dont sort, 1 = from old to the new, -1 = from new to the old.
            'order_by_date': -1,
            # 'skip_until': '5UoJqCbGDRk',
            # 'skip_until': 'cEBzmMkgJ9s',  # EmYeOBoLhYs
            'forced_mtime': 0,  # reset comments date by video file date, True/False
            'skip_existing': 1,  # True/False
            'min_new_comments': 5,
            'min_new_comments_perc': 2,  # % новых комментов
            'update_if_negative': 2,
            'convert_to_text': 1,
        }
        go_scan(start_path, opts)
