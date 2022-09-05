import os, random, datetime, urllib.request, json, glob, shutil, subprocess, getopt, sys
from random import randint

IGNORE_SHOWS = {
    'Chai Time',
    'Palo Alto City Council',
}

STAGE_DIR = "/Users/Barbara/GoogleDrive/My Drive/show_uploads/"
show_date = datetime.datetime.now()
create_files = False

TUESDAY_GAPS = [[6,4], [19,1], [22,1]]
THURSDAY_GAPS= [[6,3], [11.5, 6.5], [7,1]]
DAY_GAPS = {1:TUESDAY_GAPS, 3:THURSDAY_GAPS}

def parse_args(argv):
   global show_date, create_files

   try:
      opts, args = getopt.getopt(argv,"d:c:",["date", "create-files"])
   except getopt.GetoptError:
      print ('test.py -d YYYY-MM-DD')
      sys.exit(2)

   for opt, arg in opts:
      if opt == '-h':
         print ('test.py -date YYYY-MM-DD')
         sys.exit()
      elif opt in ("-d", "--date"):
         is_today = False
         show_date = datetime.datetime.strptime(arg, "%Y-%m-%d")
      elif opt in ("-c", "--create_files"):
         is_test = True

   print ('Show date: {}'.format(show_date))

# return time length in seconds of an mp3 file using ffmpeg or -1 if invalid.
# assumes user has ffmpeg in PATH.
def execute_ffmpeg_command(cmd):
    cmd = "/usr/local/bin/ffmpeg -hide_banner " + cmd
    print("Execute: {}".format(cmd))
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    (output, err) = p.communicate()
    p_status = p.wait()
    err = str(err)

    print("Execute: returned {}, {}".format(output, err))
    return p_status

def get_mp3_duration(filePath):
    duration = -1
    cmd = "/usr/local/bin/ffmpeg -hide_banner -i '" + filePath + "'"
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    (output, err) = p.communicate()
    p_status = p.wait()
    err = str(err)

    print("Execute: {} returned {}, {}".format(cmd, output, err))
    if err.find("Duration:") > 0:
        time_str = err
        idx1 = time_str.index('Duration:') + 9
        idx2 = time_str.index(',', idx1)
        time_str = time_str[idx1:idx2].strip()
        time = datetime.datetime.strptime(time_str, '%H:%M:%S.%f')
        duration = time.second + time.minute * 60 + time.hour * 3600

    is_44100Hz = err.find('44100 Hz') > 0
    return (duration, is_44100Hz)


def add_disclaimer_and_copy(srcFile, destFile, durationMins):
    retFile = None
    INSERT_GAP = 30*60 #seconds
    TMP_PATH = 'disclaimer_file'
    retFile = None
    (durationSeconds, is44100Hz) = get_mp3_duration(srcFile)

    if durationSeconds < 0:
        return retFile

    startTime = 0
    fileCnt = 0
    while startTime < durationSeconds:
        endTime = startTime + min(INSERT_GAP, durationSeconds - startTime)
        tmpFile = TMP_PATH + str(fileCnt) + '.mp3'
        cmd = '-y  -i "{}" -ss {} -to {} -c:a copy {}'.format(srcFile, startTime, endTime, tmpFile)
        if execute_ffmpeg_command(cmd) != 0:
            return None

        startTime = endTime
        fileCnt = fileCnt + 1


    cmd = '-y -i "concat:'
    sepChar = ''
    disclaimFile = 'disclaimer44100.mp3' if is44100Hz else 'disclaimer48000.mp3'
    for i in range(fileCnt):
        cmd = cmd + '{}{}|{}{}.mp3'.format(sepChar, disclaimFile, TMP_PATH, i)
        sepChar = '|'

    rootName = os.path.basename(srcFile)[0:-4]
    cmd = cmd + '" -acodec copy -t {} -metadata title="{}" "{}"'.format(durationMins*60, rootName, destFile)
    if execute_ffmpeg_command(cmd) == 0:
        retFile = destFile
    elif os.path.exists(destPath):
        os.rename(destFile, destFile + ".bad")

    return retFile


def fill_gap(gap_datetime, gap_hours):
    show_files = []
    idx = 1000
    summary_msg = ''
    while gap_hours > 0 and idx > 0:
        idx = idx - 1
        (showdate, show_filepath) = get_show_file(False)
        if show_filepath == None:
            break

        showdate = datetime.datetime.strptime(show_filepath[-19:-4], "%Y-%m-%d-%H%M")
        showinfo = get_show_info(showdate)
        if not showinfo or showinfo['attributes']['name'] in IGNORE_SHOWS:
            continue

        glob_path = STAGE_DIR + gap_datetime.strftime("%Y-%m-%d_%H%M*.mp3")
        duration_minutes = 60 - gap_datetime.minute
        glob_ar = glob.glob(glob_path)
        if len(glob_ar) > 0:
            summary_msg = summary_msg + "Slot filled: {} \n".format(glob_ar[0])
        else:
            end_hour = gap_datetime.hour + 1
            show_filename = os.path.basename(show_filepath)
            stage_filename = gap_datetime.strftime("%Y-%m-%d_%H%M") + "-{:02}00_{}".format(end_hour, show_filename)
            stage_filepath = STAGE_DIR + stage_filename
            summary_msg = summary_msg + "Stage: {}, {}\n".format(show_filename, stage_filename)
            if create_files:
                add_disclaimer_and_copy(show_filepath, stage_filepath, duration_minutes)

        gap_datetime = gap_datetime + datetime.timedelta(minutes=duration_minutes)
        gap_hours = gap_hours - duration_minutes/60.0

    print(summary_msg)
    return gap_hours == 0


def get_time_from_zookeeper(time_str):
    hour = float(time_str[0:2]) + float(time_str[2:4])/60.0
    return hour

def get_show_info(showdate):
    day_info = None
    url = 'https://zookeeper.stanford.edu/api/v1/playlist?filter[date]=' + showdate.strftime('%Y-%m-%d')
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


# return True if this is a good time for a potential source file, e.g.
# not safe harbor, early morning (usually Zootopia) or PACC.
def is_safe_showdate(showdate, is_safeharbor):
    MONDAY_IDX = 0
    isBad = showdate.hour > 1 and showdate.hour < 7 or \
            is_safeharbor == False and (hour >= 22 or hour < 6) or \
            showdate.weekday == MONDAY_IDX and hour >=  17

    return isBad == False


def random_datetime(start, end):
    rand_seconds = random.randint(0, int((end - start).total_seconds()))
    date = start + datetime.timedelta(seconds=rand_seconds)
    return date

def get_show_file(safe_harbor):
    FILE_ROOT = '/Volumes/Public/kzsu-aircheck-archives/'
    start_date = datetime.datetime(2012, 2, 16)
    end_date = datetime.datetime.now() - datetime.timedelta(hours=24)

    ######
    #return (datetime.datetime(2022, 3, 3, 12), '/Users/Barbara/tmp/kzsu-archive/2022/Mar/03/kzsu-2022-03-03-1200.mp3')

    idx = 0
    while idx < 1000:
        idx = idx + 1
        showdate = random_datetime(start_date, end_date)
        showfile = showdate.strftime('%Y/%b/%d/kzsu-%Y-%m-%d-%H00.mp3')

        hour = showdate.hour
        if is_safe_showdate(shodate, safe_harbor):
            continue

        file_path = FILE_ROOT + showfile
        if os.path.exists(file_path):
            return (showdate, file_path)

    return (None, None)

if __name__ == '__main__':
    parse_args(sys.argv[1:])
    gaps = 0
    weekday = show_date.weekday()
    gap_ar = DAY_GAPS.get(weekday, [])
    for gap in gap_ar:
        gap_datetime = show_date + datetime.timedelta(hours=gap[0])
        fill_gap(gap_datetime, gap[1])
