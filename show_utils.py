import os, random, datetime, urllib.request, json
from random import randint

def get_time_from_zookeeper(time_str):
    hour = float(time_str[0:2]) + float(time_str[2:4])/60.0
    return hour

def get_show_info(showdate):
    day_info = None
    url = 'https://zookeeper.stanford.edu/api/v1/playlist?filter[date]=' + showdate.strftime('%Y/%m/%d')
    response = urllib.request.urlopen(url)
    if response.status != 200:
        return None

    day_info = json.loads(response.read())
    start_hour = showdate.hour
    for show in day_info['data']:
        attributes = show['attributes']
        time_ar = attributes['time'].split('-')
        show_start = get_time_from_zookeeper(time_ar[0])
        show_end = get_time_from_zookeeper(time_ar[1])
        show_end = show_end + 24 if show_end < show_start else show_end

        if start_hour >= show_start  and start_hour < show_end:
            return show

    return None

def random_datetime(start, end):
    rand_seconds = random.randint(0, int((end - start).total_seconds()))
    date = start + datetime.timedelta(seconds=rand_seconds)
    return date

def get_show_file(safe_harbor):
    FILE_ROOT = '/Volumes/Public/kzsu-aircheck-archives/'
    start_date = datetime.datetime(2012, 2, 16)
    end_date = datetime.datetime.now() - datetime.timedelta(hours=24)


    #return (datetime.datetime(2022, 3, 3, 12), 'test_file')   #########

    idx = 0
    while idx < 1000:
        idx = idx + 1
        showdate = random_datetime(start_date, end_date)
        showfile = showdate.strftime('%Y/%b/%d/kzsu-%Y-%m-%d-%H00.mp3')

        hour = showdate.hour
        if hour < 7 or not safe_harbor and hour >= 22:
            continue

        file_path = FILE_ROOT + showfile
        if os.path.exists(file_path):
            return (showdate, file_path)

    return (None, None)

if __name__ == '__main__':
    for i in range(10):
        (showdate, file) = get_show_file(False)
        if showdate:
            showinfo = get_show_info(showdate)
            title = 'Unknown'
            if showinfo:
                attrs = showinfo['attributes']
                title = attrs['name']

            print("show {}, {}, {}".format(showdate, file, title))
        else:
            print("No file")

