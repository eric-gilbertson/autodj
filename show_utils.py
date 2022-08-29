import os, random, datetime
from random import randint

def random_datetime(start, end):
    rand_seconds = random.randint(0, int((end - start).total_seconds()))
    date = start + datetime.timedelta(seconds=rand_seconds)
    return date

def get_show_file(safe_harbor):
    FILE_ROOT = '/Volumes/Public/kzsu-aircheck-archives/'
    start_date = datetime.datetime(2012, 2, 16)
    end_date = datetime.datetime(2022, 8, 1)

    idx = 0
    while idx < 1000:
        idx = idx + 1
        showdate = random_datetime(start_date, end_date)
        showfile = showdate.strftime('%Y/%b/%d/kzsu-%Y-%m-%d-%H00.mp3')

        hour = showdate.hour
        if hour < 6 or not safe_harbor and hour >= 22:
            continue

        file_path = FILE_ROOT + showfile
        if os.path.exists(file_path):
            return file_path

        print("skip")

    return None

if __name__ == '__main__':
    for i in range(10):
        file = get_show_file(False)
        print("show file: {}".format(file))

