#!/usr/bin/python3
#
# fills holes in program queue by filling the gaps with randomally selected
# files from the program archive ignoring the files defined in 
# ZOOKEEPER_IGNORE_PLAYLISTS. Also sanity check potential files for size and
# silence gaps in order to eliminate corrupt and inappropriate files. 
#
import os, random, datetime, urllib.request, json, glob, shutil, subprocess, getopt, sys
import http.client
from random import randint
from add_disclaimer import insert_disclaimer

# TODO:
# don't give given DJ more than one show
# check that PL runs full hour

# list of Zookeeper playlists that should not be rebroadcasted truncated to
# 15 characters. note these names may differ from the scheduled show name.
# NOTE: keys are truncated to 15 characters and set to lower case on startup.
ZOOKEEPER_IGNORE_PLAYLISTS_SOURCE = [
    '',
    'MHz',
    'MHz broadcast',
    'MHz presents ',
    'Zootopia',
    'Chaitime',
    'Blues With a feeling',
    'Laptop Radio',
    'Time Traveler',
    'Radio Survivor',
    'KZSU Time Trave',
    'LIVE!! KZSU Tim',
    'Urban Innercity',
    'The Urban Innercity',
    'University Publ',
    'Philosophy Talk',
    'Planetary Radio',
    'NOT THE Palo Alto City Council',
    'Viewer Discretion Advised',
    'Commencement',
]

ZOOKEEPER_IGNORE_AIRNAMES = [
    'Francis D', # doesn't want to be rebroadcasted
    'LJH Collage Crew',
    'Raymundo',  # FCCs
    'M-SMOOTH',   # FCCs
]

DJ_CACHE = {}
SHOW_CACHE = {}
PLAYLIST_KEY_MAX_LEN=15
ZOOKEEPER_IGNORE_PLAYLISTS = {}

#STAGE_DIR = "/Users/Barbara/GoogleDrive/My Drive/show_uploads/"
STAGE_DIR = "/Volumes/GoogleDrive/My Drive/show_uploads/"

show_date = datetime.datetime.now()
create_files = False

def get_vault_shows(dateStr):
    gaps = []
    connection = http.client.HTTPConnection('kzsu.stanford.edu', timeout=2)
    url = '/api/shows/bydate/{}/'.format(dateStr)
    connection.request('GET', url)
    respObj = json.load(connection.getresponse())
    shows = respObj['day']['shows']
    for show in shows:
        if show['title'].lower() == 'from the vault' or show['needs_sub']:
            kzsuStart = show['start_time']
            startTime = float(kzsuStart[0:2]) + (float(kzsuStart[2:4]) / 60.0)
            durationHours = int(show['duration']) / 60.0
            gaps.append([startTime, durationHours])

    print("Found {} vault shows for {}".format(len(gaps), dateStr))
    return gaps

        
# gaps are defined as [<START_HOUR>, <DURATION_HOURS>]
TUESDAY_GAPS = [[6,4], [21,1]]
THURSDAY_GAPS= [[6,3], [18, 2]]
DAY_GAPS = {1:TUESDAY_GAPS, 3:THURSDAY_GAPS}

def parse_args(argv):
   global show_date, create_files

   try:
      opts, args = getopt.getopt(argv,"d:c:",["date", "create-files"])
   except getopt.GetoptError:
      print ('Parse error: usage {} -d YYYY-MM-DD'.format(argv[0]))
      sys.exit(2)

   for opt, arg in opts:
      if opt == '-h':
         print (argv[0] + ' -date YYYY-MM-DD')
         sys.exit()
      elif opt in ("-d", "--date"):
         is_today = False
         show_date = datetime.datetime.strptime(arg, "%Y-%m-%d")
      elif opt in ("-c", "--create_files"):
         create_files = True

   #print ('Show date: {}, {}'.format(show_date, create_files))

# return time length in seconds of an mp3 file using ffmpeg or -1 if invalid.
# assumes user has ffmpeg in PATH.
def execute_ffmpeg_command(cmd):
    cmd = "/usr/local/bin/ffmpeg -hide_banner " + cmd
    #print("Execute: {}".format(cmd))
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    (output, err) = p.communicate()
    p_status = p.wait()
    err = str(err)

    #print("Execute: returned {}, {}".format(output, err))
    return p_status

def get_mp3_duration(filePath):
    duration = -1
    cmd = "/usr/local/bin/ffmpeg -hide_banner -i '" + filePath + "'"
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    (output, err) = p.communicate()
    p_status = p.wait()
    err = str(err)

    #print("Execute: {} returned {}, {}".format(cmd, output, err))
    if err.find("Duration:") > 0:
        time_str = err
        idx1 = time_str.index('Duration:') + 9
        idx2 = time_str.index(',', idx1)
        time_str = time_str[idx1:idx2].strip()
        time = datetime.datetime.strptime(time_str, '%H:%M:%S.%f')
        duration = time.second + time.minute * 60 + time.hour * 3600

    is_44100Hz = err.find('44100 Hz') > 0
    return (duration, is_44100Hz)


#def add_disclaimer_and_copy(srcFile, destFile, durationMins):
#    retFile = None
#    INSERT_GAP = 30*60 #seconds
#    TMP_PATH = 'disclaimer_file'
#    retFile = None
#    (durationSeconds, is44100Hz) = get_mp3_duration(srcFile)
#
#    if durationSeconds < 0:
#        return retFile
#
#    startTime = 0
#    fileCnt = 0
#    while startTime < durationSeconds:
#        endTime = startTime + min(INSERT_GAP, durationSeconds - startTime)
#        tmpFile = TMP_PATH + str(fileCnt) + '.mp3'
#        cmd = '-y  -i "{}" -ss {} -to {} -c:a copy {}'.format(srcFile, startTime, endTime, tmpFile)
#        if execute_ffmpeg_command(cmd) != 0:
#            return None
#
#        startTime = endTime
#        fileCnt = fileCnt + 1
#
#
#    cmd = '-y -i "concat:'
#    sepChar = ''
#    disclaimFile = 'disclaimer44100.mp3' if is44100Hz else 'disclaimer48000.mp3'
#    for i in range(fileCnt):
#        cmd = cmd + '{}{}|{}{}.mp3'.format(sepChar, disclaimFile, TMP_PATH, i)
#        sepChar = '|'
#
#    rootName = os.path.basename(srcFile)[0:-4]
#    cmd = cmd + '" -acodec copy -t {} -metadata title="{}" "{}"'.format(durationMins*60, rootName, destFile)
#    if execute_ffmpeg_command(cmd) == 0:
#        retFile = destFile
#    elif os.path.exists(destFile):
#        os.rename(destFile, destFile + ".bad")
#
#    return retFile

# return pair of floats representing the show start & end times including minutes
def get_show_hours_from_zookeeper(time_range):
    start_hour = float(time_range[0:2]) + int(time_range[2:4])/60.0
    end_hour = float(time_range[5:7]) + int(time_range[7:9])/60.0
    return (start_hour, end_hour)

def fill_gap(gap_datetime, gap_hours):
    show_files = []
    idx = 1000
    summary_msg = ''
    while gap_hours > 0 and idx > 0:
        idx = idx - 1
        (showdate, show_filepath) = get_show_file(False)
        if show_filepath == None:
            print("Error: no show files available.")
            break

        showdate_str = show_filepath[-19:-4]
        showdate = datetime.datetime.strptime(showdate_str, "%Y-%m-%d-%H%M")
        showinfo = get_show_info(showdate)
        showname = showinfo['attributes']['name'] if showinfo else ''
        airname = showinfo['attributes']['airname'] if showinfo else ''

        # use truncated compare becase names can have show specific suffixes.
        shortname = showname[0:PLAYLIST_KEY_MAX_LEN].strip().lower()
        if shortname in ZOOKEEPER_IGNORE_PLAYLISTS or showname.lower().find('rebroadcast') >= 0 or airname in ZOOKEEPER_IGNORE_AIRNAMES or shortname in SHOW_CACHE:
            if len(showname) > 0:
                print("Skip show {}".format(showname))

            continue

        SHOW_CACHE[shortname] = True
        show_attributes = showinfo['attributes']
        show_shortname = showname[0:20].strip()
        glob_path = STAGE_DIR + gap_datetime.strftime("%Y-%m-%d_%H%M*.mp3")
        duration_minutes = 60 - gap_datetime.minute
        (show_starthour, show_endhour) = get_show_hours_from_zookeeper(show_attributes['time'])
        glob_ar = glob.glob(glob_path)
        if len(glob_ar) > 0:
            #summary_msg = summary_msg + "Slot filled: {} \n".format(glob_ar[0])
            pass
        else:
            # this check is last because it is expensive
            msg = check_audio_quality(show_filepath, 60)
            if msg != 'ok':
                print('Audio check error: {}, {}'.format(filepath, msg))
                continue

            end_hour = gap_datetime.hour + 1
            stage_start = gap_datetime.strftime("%Y-%m-%d_%H%M")
            stage_filename = stage_start + "-{:02}00_{}-{}.mp3".format(end_hour, show_shortname, showdate_str)
            stage_filepath = STAGE_DIR + stage_filename
            summary_msg = summary_msg + "Stage: {}, {}, {}\n".format(os.path.basename(show_filepath), stage_start, showname)
            if create_files:
                insert_disclaimer(show_filepath, stage_filepath)

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
    hour = showdate.hour
    isBad = hour > 1 and hour < 7 or \
            is_safeharbor == False and (hour >= 22 or hour < 6) or \
            showdate.weekday == MONDAY_IDX and hour >=  17

    return isBad == False


def random_datetime(start, end):
    rand_seconds = random.randint(0, int((end - start).total_seconds()))
    date = start + datetime.timedelta(seconds=rand_seconds)
    return date

# return ok if file appears to be playable else a status string indicating the issues
def check_audio_quality(filePath, expected_length_mins):
    msg = ''
    duration = -1
    cmd = '/usr/local/bin/ffmpeg -hide_banner -i "{}"  -af silencedetect=n=-30dB:d=120.0 -f null -'.format(filePath)
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    (output, err) = p.communicate()
    p_status = p.wait()
    result = str(err)

    silence_start_idx = result.find('silence_start: ') + 15
    msg_prefix = 'Has silence gap: '
    while silence_start_idx > 15:
        silence_start_idx2 = result.find('.', silence_start_idx)
        start_time = result[silence_start_idx:silence_start_idx2]
        start_time = int(start_time)
        silence_end_idx = int(result.find('silence_end: ', silence_start_idx) + 13)
        silence_end_idx2 = result.find('.', silence_end_idx)
        end_time = result[silence_end_idx:silence_end_idx2]
        end_time = int(end_time)
        msg = msg + '{} {:02d}:{:02d}-{:02d}:{:02d}'.format(msg_prefix, start_time//60, start_time%60, end_time//60, end_time%60)
        msg_prefix = ', '
        silence_start_idx = result.find('silence_start: ', silence_start_idx) + 15

    if len(msg) > 0:
        msg = msg + '\n'


    if result.find("Duration:") > 0:
        idx1 = result.index('Duration:') + 9
        idx2 = result.index(',', idx1)
        time_str = result[idx1:idx2].strip()
        time = datetime.datetime.strptime(time_str, '%H:%M:%S.%f')
        seconds = time.second + time.minute * 60 + time.hour * 3600
        if abs(seconds - expected_length_mins * 60) > 120:
            msg = msg + 'Improper duration. '
    else:
        msg = msg + 'Unknown duration.'

    return msg if len(msg) > 0 else 'ok'

def is_valid_segment_file(filepath):
   
    if not os.path.exists(filepath):
        return False

    if os.path.getsize(filepath) < 40000000:
        print("Too small: " + filepath)
        return False

    return True

     
def get_show_file(safe_harbor):
    FILE_ROOT = '/Volumes/Public/kzsu-aircheck-archives/'
    start_date = datetime.datetime(2012, 2, 16)
    end_date = datetime.datetime.now() - datetime.timedelta(hours=24)

    ###### TESTING ONLY #########
    #return (datetime.datetime(2022, 3, 3, 13), '/Users/Barbara/tmp/kzsu-archive/2022/Mar/03/kzsu-2022-03-03-1300.mp3')

    idx = 0
    while idx < 1000:
        idx = idx + 1
        showdate = random_datetime(start_date, end_date)
        showfile = showdate.strftime('%Y/%b/%d/kzsu-%Y-%m-%d-%H00.mp3')

        hour = showdate.hour
        if not is_safe_showdate(showdate, safe_harbor):
            continue

        file_path = FILE_ROOT + showfile
        if is_valid_segment_file(file_path):
            return (showdate, file_path)

    return (None, None)

if __name__ == '__main__':
    parse_args(sys.argv[1:])
    if len(sys.argv) < 2:
        print('Usage {} -d YYYY-MM-DD -c [True|False]'.format(sys.argv[0]))
        sys.exit(0)

    gaps = 0
    weekday = show_date.weekday()

    # copy into new map the truncated keys so that we get those with
    # suffix and spacing variations.
    for key in ZOOKEEPER_IGNORE_PLAYLISTS_SOURCE:
        newkey = key[0:PLAYLIST_KEY_MAX_LEN].strip().lower()
        ZOOKEEPER_IGNORE_PLAYLISTS[newkey] = True

    show_date_str = datetime.datetime.strftime(show_date, '%Y-%m-%d')
    gap_ar = get_vault_shows(show_date_str)
    if len(gap_ar) == 0:
        print('No vault gaps for: ' + show_date_str)
        sys.exit(0)

    for gap in gap_ar:
        gap_datetime = show_date + datetime.timedelta(hours=gap[0])
        fill_gap(gap_datetime, gap[1])
