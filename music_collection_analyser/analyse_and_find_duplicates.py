from collections import defaultdict

import matplotlib.pyplot as plt
import datetime
import numpy as np

import plotly.graph_objects as go

import os
import pickle
import sys
from functools import partial
from queue import PriorityQueue, Full, Empty

COLLECTION_ROOTS = 'B:/Music;F:/music'

# Cache options
USE_CACHE = not True
FORCE_RESCAN = False
STORAGE_FILE = './scanned.data'
OVERWRITE_EXISTING = True

# Optional actions
FIND_DUPLICATES = True
SORT_DUPLICATES_BY_SIZE = True
PLOT = True
IMAGES_DIR = './images'

# Limits
LIMIT_SCAN_FIRST_N = 0
PRINT_MAX_FOUND_N = 0
PRINT_MAX_DUPLICATES_N = 0
TOP_MAX_SIZE_DIRS_L1_N = 15
TOP_MAX_SIZE_DIRS_L2_N = 20
TOP_MAX_SIZE_DIRS_L3_N = 30
INITIAL_YEAR = 2018
CURRENT_YEAR = 2020

# ====================
MUSIC_EXTS = {'wav', 'mp3', 'flac', 'ape', 'iso', 'dff', 'dts', 'dsf', 'dts', 'wav', 'wv', 'm4a'}

MIN_YEAR = INITIAL_YEAR

bytes_in_mb = 1024 * 1024


def getFolderSize(p):
    prepend_dir = partial(os.path.join, p)
    return sum([(os.path.getsize(f) if os.path.isfile(f) else getFolderSize(f))
                for f in map(prepend_dir, os.listdir(p))])


class DirNode:
    def __init__(self, name, size=0, fmt='', time=0):
        self.subdirs = []
        self.size = size
        self.lossy = True
        self.fmt = fmt
        self.genre = ''
        self.time = time
        self.name = name


class Scanner:
    def __init__(self, roots):
        self.roots = roots
        self.content_dirs = DirNode('Scan results')
        self.changed = False
        self.fmt_sizes = self.get_empty_fmt_stats()
        self.count = 0
        self.parent = None

    def do_op(self, op, in_depth=True, max_level=0):

        def do_op_recursive(level, dir, parent_node):
            if level > max_level > 0:
                return
            if in_depth:
                op(level, dir, parent_node)
            for subdir in dir.subdirs:
                do_op_recursive(level + 1, subdir, dir)
            if not in_depth:
                op(level, dir, parent_node)

        do_op_recursive(0, self.content_dirs, None)

    def find_duplicates(self):
        print('')
        print('Searching for duplicates...')
        duplicates = set()
        all_items = set()

        def process(_level, dir, parent_node):
            dir.parent = parent_node
            if dir.fmt:
                item = (dir.name, dir.size)
                if item in all_items:
                    duplicates.add(item)
                else:
                    all_items.add(item)

        self.do_op(process)

        if duplicates:
            print('Found %d duplicates:' % len(duplicates))
        else:
            print('No duplicates.')
        dup_paths = defaultdict(list)
        dup_size = defaultdict(list)

        def get_full_dir_path(dir, path):
            current = dir.name
            if dir.parent is not None:
                return os.path.join(get_full_dir_path(dir.parent, path), current)
            return os.path.join(path, current)

        def process2(_level, dir, _parent_node):
            item = (dir.name, dir.size)
            if item in duplicates:
                dup_paths[item].append(get_full_dir_path(dir, ''))
                dup_size[item].append(dir.size)

        self.do_op(process2)
        possible_loss = sum([sum(v[1:]) for v in dup_size.values()])
        print('Possible duplicates size: %.3d MB' % (possible_loss / bytes_in_mb))

        cnt = 0
        dup_paths_items = list(dup_paths.items())
        if SORT_DUPLICATES_BY_SIZE:
            dup_paths_items = sorted(dup_paths_items, key=lambda x: -(x[0][1]))
        for item, paths in dup_paths_items:
            dup_item, dup_item_size = item
            print('')
            print('[%.4d] %s - %.3f MB' % (cnt, dup_item, dup_item_size / bytes_in_mb))
            for p in paths:
                print(os.path.join(p, dup_item))
            cnt += 1
            if cnt > PRINT_MAX_DUPLICATES_N > 0:
                break

    def print_fmt_sizes(self):
        print('')
        print('Size by format:')
        for fmt, cnt in sorted(self.fmt_sizes.items(), key=lambda x: -x[1]):
            print(fmt, '->', int(cnt / bytes_in_mb), 'MB')

    def draw_fmt_sizes(self, images_dir):
        actual_dist = sorted(self.fmt_sizes_by_year[CURRENT_YEAR].items(), key=lambda x: -x[1])
        sorted_fmts = list(map(lambda x: x[0], actual_dist))
        total_tb = sum(self.fmt_sizes.values()) / (bytes_in_mb * bytes_in_mb)
        fig = go.Figure()
        years = self.fmt_sizes_by_year.keys()
        colors = plt.cm.get_cmap(name='prism', lut=len(years))
        for i, year in enumerate(years):
            size_counts = [self.fmt_sizes_by_year[year][fmt] for fmt in sorted_fmts]
            c = list(map(int, np.array(colors(i)[:3]) * 255))
            trace_label = '%d' % year if year > INITIAL_YEAR or INITIAL_YEAR == MIN_YEAR else \
                '%d-%d' % (MIN_YEAR, year)
            fig.add_trace(go.Bar(x=sorted_fmts,
                                 y=size_counts,
                                 name=trace_label, marker_color='rgb' + str((c[0], c[1], c[2]))
                                 ))
        fig.update_layout(
            title='Music collection by format, year & size (log scale)',
            xaxis_tickfont_size=14,
            yaxis=dict(
                type='log',
                title='Size',
                titlefont_size=16,
                tickfont_size=14,
            ),
            xaxis=dict(
                title='Total size %.3f TB /// %s' %
                      (total_tb, datetime.datetime.now().strftime('%Y-%m-%d %H:%M')),
                titlefont_size=16,
                tickfont_size=14,
            ),
            legend=dict(
                x=1,
                y=1,
                bgcolor='rgba(255, 255, 255, 0)',
                bordercolor='rgba(255, 255, 255, 0)'
            ),
            barmode='stack',
            bargap=0.15,
            bargroupgap=0.1
        )
        # fig.show()
        image_path = os.path.join(images_dir, 'fmt_sizes.png')
        fig.write_image(file=open(image_path, 'wb'), format='png')

    @staticmethod
    def get_empty_fmt_stats():
        return {fmt: 0 for fmt in MUSIC_EXTS}

    def calc_sizes(self):
        self.fmt_sizes = self.get_empty_fmt_stats()

        self.fmt_sizes_by_year = {year: self.get_empty_fmt_stats() for year in range(INITIAL_YEAR, CURRENT_YEAR + 1)}

        q1 = PriorityQueue(maxsize=TOP_MAX_SIZE_DIRS_L1_N)
        q2 = PriorityQueue(maxsize=TOP_MAX_SIZE_DIRS_L2_N)
        q3 = PriorityQueue(maxsize=TOP_MAX_SIZE_DIRS_L3_N)

        def range_size(level, dir, _parent):
            if level == 1:
                q = q1
            elif level == 2:
                q = q2
            elif level == 3:
                q = q3
            else:
                return
            while True:
                try:
                    q.put((dir.size, dir), block=False)
                    break
                except Full:
                    q.get()

        def clr_size(_level, _dir, parent):
            if parent:
                parent.size = 0

        def set_size(_level, dir, parent):
            if parent:
                sz = dir.size
                fmt = dir.fmt
                if fmt:
                    self.fmt_sizes[fmt] += sz
                    year = datetime.datetime.utcfromtimestamp(dir.time).year
                    if year < INITIAL_YEAR:
                        global MIN_YEAR
                        if MIN_YEAR > year:
                            MIN_YEAR = year
                        year = INITIAL_YEAR
                    elif year > CURRENT_YEAR:
                        year = CURRENT_YEAR
                    self.fmt_sizes_by_year[year][fmt] += sz
                parent.size += sz

        self.do_op(clr_size, in_depth=False)
        self.do_op(set_size, in_depth=False)
        self.do_op(range_size, in_depth=False, max_level=3)
        for l, q in enumerate([q1, q2, q3]):
            print('')
            print('Top level-%d sized dirs:' % (l + 1))
            dirs = []
            while True:
                try:
                    item = q.get(block=False)
                except Empty:
                    break
                dirs.append(item[1])
            for i, dir in enumerate(reversed(dirs)):
                print('%.2d' % (i + 1), dir.name, ' - %d MB' % (dir.size / bytes_in_mb))

    def print_found(self):
        print('')
        print('Total %d folders' % self.count)
        cnt = 0

        def prnt(level, dir, _parent):
            mb = dir.size / bytes_in_mb
            nonlocal cnt
            cnt += 1
            if cnt > PRINT_MAX_FOUND_N:
                raise StopIteration

            print(' ' * (2 * level) + dir.name + ' - %d MB' % mb)

        try:
            self.do_op(prnt)
        except StopIteration:
            pass

    def scan(self):
        print('Scan started')
        self.check_roots()
        old_count = self.count
        self.count = 0

        def scan_root(root):
            if LIMIT_SCAN_FIRST_N > 0 and self.count > LIMIT_SCAN_FIRST_N:
                return []
            files = os.listdir(root)
            dirs = []
            root_dirname = os.path.basename(root)
            content_dirs = DirNode(root_dirname)
            for filename in files:
                full_path = os.path.join(root, filename)
                if os.path.isdir(full_path):
                    dirs.append(filename)
                else:
                    _base, ext = os.path.splitext(filename)
                    if ext.startswith('.'):
                        ext = ext[1:]
                    ext = ext.lower()
                    if ext in MUSIC_EXTS:
                        self.count += 1
                        if self.count % 1000 == 0:
                            print('Scanned %d elements, current:' % self.count, root)
                        content_dir = DirNode(root_dirname,
                                              fmt=ext,
                                              size=getFolderSize(root),
                                              time=os.stat(root).st_mtime)
                        return content_dir

            for d in dirs:
                full_path = os.path.join(root, d)
                if os.path.isdir(full_path):
                    subdir = scan_root(full_path)
                    if subdir:
                        content_dirs.subdirs.append(subdir)
            if content_dirs.subdirs:
                return content_dirs
            else:
                return None

        for r in self.roots:
            subdir = scan_root(r)
            if subdir:
                self.content_dirs.subdirs.append(subdir)

        self.changed = self.count != old_count

    def check_roots(self):
        fail = False
        for r in self.roots:
            if not os.path.exists(r):
                print('Missing', r)
                fail = True
        if fail:
            print('exit')
            sys.exit(1)
        else:
            print('Roots checked OK')

    @staticmethod
    def load(storage_file):
        print('Loading cache', storage_file)
        return pickle.load(open(storage_file, 'rb'))

    def save(self, storage_file):
        if self.changed:
            print('Saving changes to', storage_file)
            self.changed = False
            pickle.dump(self, open(storage_file, 'wb'))
        else:
            print('Scan results not changed')


if __name__ == "__main__":
    storage_file = STORAGE_FILE
    use_cache = USE_CACHE
    force_rescan = FORCE_RESCAN
    overwrite_existing = OVERWRITE_EXISTING

    cache_loaded = False
    if use_cache and os.path.exists(storage_file):
        scanner = Scanner.load(storage_file)
        cache_loaded = True
    else:
        roots = COLLECTION_ROOTS.split(';')
        print('roots:', roots)
        scanner = Scanner(roots)

    if force_rescan or not cache_loaded:
        try:
            scanner.scan()
        except (KeyboardInterrupt, Exception):
            print('Break pressed')

    images_dir = IMAGES_DIR
    if not os.path.exists(images_dir):
        os.makedirs(images_dir, exist_ok=True)
    scanner.calc_sizes()
    scanner.print_found()
    scanner.print_fmt_sizes()
    if FIND_DUPLICATES:
        scanner.find_duplicates()
    if PLOT:
        scanner.draw_fmt_sizes(images_dir)

    if not (overwrite_existing and os.path.exists(storage_file)):
        scanner.save(storage_file)
