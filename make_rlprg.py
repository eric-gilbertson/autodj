##!/usr/bin/python

import datetime, sys, getopt, os, shutil, commands, time, filecmp
from array import *
import glob
import urllib

HOME_DIR = os.getenv("HOME")
GDRIVE_PATH = '/Volumes/GoogleDrive/My Drive'
#GDRIVE_PATH = '/Users/Barbara/studioq'
CACHE_DIR = HOME_DIR + '/Music/show_cache'

RLDJ_HOME = HOME_DIR + '/Music/Radiologik'
RLDJ_SCRIPTS = RLDJ_HOME + '/Scripts/'

# NOTE: the tabs in the following defines ARE REQUIRED.
SILENCE_FILE = '	file://' + urllib.quote(CACHE_DIR + '/silence.aiff')
OUTRO_FILE = CACHE_DIR + '/show_fill.mp3'

START_AUTODJ = SILENCE_FILE + '	false	-1			file:///Users/engineering/Music/Radiologik/Scripts/AutodjOn.applescript			Autodj - on'

START_AUTODJ_TIMED = SILENCE_FILE + '	squeeze	{0}			file:///Users/engineering/Music/Radiologik/Scripts/AutodjOn.applescript			Autodj - on'

START_BREAK = SILENCE_FILE + '	false	{0}						Time Break'

STOP_ZOOTOPIA = SILENCE_FILE + '	false	{0}	2					Zootopia - off'
START_ZOOTOPIA_TIMED = SILENCE_FILE + '	false	{0}	1					ZootopiaInt - on'
START_ZOOTOPIA = SILENCE_FILE + '	false	-1	1					Zootopia - on'
PLAY_PROGRAM  = '	file://{}	false	-1					{}'

UPLOAD_DIR = GDRIVE_PATH + '/show_uploads/'

is_today = True
run_immediate = False

show_date = datetime.datetime.now().strftime("%Y-%m-%d")

# parse show file entry into a structure
class ShowInfo():
    def __init__(self, show_line):
        log_it("show: " + show_line);
        file_name = show_line[len(UPLOAD_DIR):]
        info_ar = file_name.split('_')
        time_ar = info_ar[1].split('-')

        self.file_name = file_name
        self.day = info_ar[0]
        self.start_time = time_ar[0]
        self.end_time = time_ar[1]
        self.title = info_ar[2]

def log_it(msg):
    print(msg)
    timestr = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S: ")
    with open('/tmp/make_rlprg_log.txt', 'a') as logfile:
        logfile.write(timestr + msg + '\n')


def parse_args(argv):
   global show_date, is_today

   try:
      opts, args = getopt.getopt(argv,"d:",["date"])
   except getopt.GetoptError:
      log_it ('test.py -d YYYY-MM-DD')
      sys.exit(2)

   for opt, arg in opts:
      if opt == '-h':
         log_it ('test.py -date YYYY-MM-DD')
         sys.exit()
      elif opt in ("-d", "--date"):
         is_today = False
         show_date = arg

   log_it ('Show date: {}'.format(show_date))

# converts HH:MM to seconds into the day.
def emit_line(line):
    out_file.write(line + '\n')
    #log_it(line)

def get_rltime(time_str):
    hours = time_str[0:2]
    minutes = time_str[2:4]
    rltime = int(hours) * 3600 + int(minutes) * 60
    return rltime

def emit_zootopia_start_timed(time_str):
    rl_time = get_rltime(time_str)
    emit_line(START_ZOOTOPIA_TIMED.format(rl_time))

def emit_zootopia_start():
    emit_LID()
    emit_line(START_ZOOTOPIA)

def emit_autodj_start_timed():
    rl_time = get_rltime(time_str)
    emit_line(START_AUTODJ.format(rl_time))

def emit_zootopia_end(time_str):
    rl_time = get_rltime(time_str)
    emit_line(STOP_ZOOTOPIA.format(rl_time))

def emit_autodj_start(time_str):
    rl_time = get_rltime(time_str)
    emit_line(START_AUTODJ.format(rl_time))

def emit_break(time_str):
    rl_time = get_rltime(time_str)
    emit_line(START_BREAK.format(rl_time))

def emit_LID():
    # this file should have 1 second of lead silence becasuse of the delay
    # incurred when switching from Zootopia to AutoDJ.
    lid_file = CACHE_DIR + '/LID_KZSU_Guy.mp3'
    emit_program_play(lid_file, "LID")

def emit_program_play(show_file, show_title):
    show_file_encoded = urllib.quote(show_file)
    play_line = PLAY_PROGRAM.format(show_file_encoded, show_title)
    emit_line(play_line)

def add_extras_for_day(shows, day_ord, date_str):
    extras_path = UPLOAD_DIR + day_ord[:3] + "_*.mp3"
    extras = glob.glob(extras_path)

    for extra in extras:
        name = extra[len(UPLOAD_DIR):]
        name_suffix = name[3:]
        add_item = '{}{}{}'.format(UPLOAD_DIR, date_str, name_suffix)
        # copy is okay if files are small. reconsider if the get large.
        if not os.path.isfile(add_item):
            shutil.copy(extra, add_item)
            log_it(" add: " + add_item)
            shows.append(add_item)

# return duration in seconds from KZSU time. not using Date because KZSU time ends at 3000hours.
def get_schedule_duration(start_time, end_time):
    start_seconds = int(start_time[:2]) * 3600 + int(start_time[2:]) * 60
    end_seconds = int(end_time[:2]) * 3600 + int(end_time[2:]) * 60
    return end_seconds - start_seconds


# return time length of an mp3 file using ffmpeg or -1 if invalid.
# assumes user has ffmpeg in PATH.
def get_mp3_duration(filePath):
    FFMPEG_CMD = "/usr/local/bin/ffmpeg -hide_banner "
    duration = -1
    try:
        cmd = FFMPEG_CMD + "-i '" + filePath + "'"
        ret_val = commands.getstatusoutput(cmd)
        log_it("Execute: {} returned {}, {}".format(cmd, ret_val[0], ret_val[1]))
        if ret_val[1] and ret_val[1].find("Duration:") > 0:
            time_str = ret_val[1]
            idx1 = time_str.index('Duration:') + 9
            idx2 = time_str.index(',', idx1)
            time_str = time_str[idx1:idx2].strip()
            time = datetime.datetime.strptime(time_str, '%H:%M:%S.%f')
            duration = time.second + time.minute * 60 + time.hour * 3600
    except Exception as ioe:
        log_it('Exception getting duration for: {}, {}'.format(cmd, ioe))

    return duration

# clear any older show files if doing today
def clear_show_cache():
    if not is_today:
        return

    now = datetime.datetime.now()
    now_day = now.timetuple().tm_yday
    cache_files = glob.glob('{}/{}*.mp3'.format(CACHE_DIR, now.year))
    for file in cache_files:
        mtime = time.ctime(os.path.getmtime(file))
        mdatetime = datetime.datetime.strptime(mtime, "%c")
        log_it("time: {}".format(mdatetime))
        if mdatetime.timetuple().tm_yday < now_day:
            log_it("delete cache file: " + file)
            os.remove(file)
          
def kzsutime_to_minutes(kzsu_time):
    mins = int(kzsu_time[0:2]) * 60 + int(kzsu_time[2:4])
    return mins

def minutes_to_kzsutime(minutes):
    hours = minutes // 60
    mins = minutes % 60
    kzsu_time = "{:02}{:02}".format(hours, mins)
    return kzsu_time

def endtime_from_duration(kzsu_start_time, duration_secs):
    end_mins = kzsutime_to_minutes(kzsu_start_time) + duration_secs // 60
    end_time = minutes_to_kzsutime(end_mins)
    return end_time

# copy and then compare the files. needed because we get occasional copy
# errors when copying from GDrive to the local drive.
def safe_copy(src_file, dest_file):
    log_it("copy to staging dir: {}, {}".format(src_file, dest_file))
    shutil.copy(src_file, dest_file)

    if not filecmp.cmp(src_file, dest_file, shallow=False):
        log_it("File copy error1: {}, {}".format(src_file, dest_file))
        os.remove(dest_file)
        time.sleep(5)
        shutil.copy(src_file, dest_file)
        if not filecmp.cmp(src_file, dest_file, shallow=False):
            log_it("File copy error2: {}, {}".format(src_file, dest_file))


parse_args(sys.argv[1:])
shows_path = UPLOAD_DIR + show_date + "*.mp3"
show_day = datetime.datetime.strptime(show_date, '%Y-%m-%d').strftime('%A')
is_weekend = show_day == 'Saturday' or show_day == 'Sunday'
is_sunday = show_day == 'Sunday'
out_file = open('{}/{}.rlprg'.format(UPLOAD_DIR,show_day), "w");
run_time = datetime.datetime.now().time()

clear_show_cache()

log_it('shows for {0}, {1}'.format(show_date, show_day))
shows = glob.glob(shows_path)
if len(shows) == 0:
    log_it('No shows for ' + shows_path)
    sys.exit(1)

#add_extras_for_day(shows, show_day, show_date)
shows.sort()

# TODO - get actual durations
emit_line('Duration:19807')

#TODO - handle no shows case

TIME_SKEW_SECONDS = 30
prev_end_time = False
prev_silence = False
is_first = True
for show_line in shows:
    show = ShowInfo(show_line)
    show_title = show.title
    start_time = show.start_time
    end_time = show.end_time
    length_mins = kzsutime_to_minutes(end_time) - kzsutime_to_minutes(start_time)

    # skip this check for shows after midnight (KZSU time)
    is_valid_time = int(start_time) < 2400
    if is_today and is_valid_time:
        start_time_obj = datetime.datetime.strptime(start_time, '%H%M').time()
        if start_time_obj < run_time:
            log_it("skip past show: " + show_title)
            continue

    block_start_time = start_time

    if is_first or (prev_end_time and prev_end_time != block_start_time):
        if prev_end_time:
            emit_zootopia_start()

        emit_zootopia_end(block_start_time)

        # in case autodj was enabled, e.g. PACC meeting on Monday evening.
        if is_first:
            emit_line(START_AUTODJ)

    if start_time.endswith('00'):
        emit_LID()

    cache_file = CACHE_DIR + '/' + show.file_name
    if not os.path.exists(cache_file):
        safe_copy(show_line, cache_file)
        #shutil.copyfile(show_line, cache_file)

    emit_program_play(cache_file, show_title)

    # skip this check if show start >= midnight or if start and end times are equal
    if is_valid_time and length_mins > 2:
        schedule_duration = get_schedule_duration(start_time, end_time)
        file_duration = get_mp3_duration(show_line)
        time_skew = abs(schedule_duration - file_duration)
        is_short =  file_duration < schedule_duration

        # do something if time skew > 30 seconds
        if file_duration > 0 and time_skew > TIME_SKEW_SECONDS:
            # if gt 5 minutes then turn zootopia back on and adjust end time.
            if is_short:
                if time_skew > 300:
                    end_time = endtime_from_duration(start_time, file_duration)
                else:
                    if file_duration < schedule_duration:
                        emit_program_play(OUTRO_FILE, "outro")

                    emit_break(end_time)
            elif time_skew > TIME_SKEW_SECONDS:
                emit_break(end_time)

    is_first = False
    prev_end_time = end_time

# reenable Zootopia
emit_zootopia_start()

out_file.close()



