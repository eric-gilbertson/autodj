##!/usr/bin/python

import datetime, sys, getopt, os, shutil
from array import *
import glob
import urllib

GDRIVE_PATH = '/Volumes/GoogleDrive/My Drive'

RLDJ_HOME = os.getenv("HOME") + '/Music/Radiologik'
RLDJ_SCRIPTS = RLDJ_HOME + '/Scripts/'

# NOTE: the tabs in the following defines ARE REQUIRED.
SILENCE_FILE = '	file://' + urllib.quote(GDRIVE_PATH + '/show_uploads/silence.aiff')
OUTRO_FILE = '/Volumes/GoogleDrive/My Drive/show_uploads/show_fill.mp3'

SPOTBOX_PATH = GDRIVE_PATH + '/spotbox audio'

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
        print("show: " + show_line);
        file_name = show_line[len(UPLOAD_DIR):]
        info_ar = file_name.split('_')
        time_ar = info_ar[1].split('-')

        self.day = info_ar[0]
        self.start_time = time_ar[0]
        self.end_time = time_ar[1]
        self.title = info_ar[2]


def parse_args(argv):
   global show_date, is_today

   try:
      opts, args = getopt.getopt(argv,"d:",["date"])
   except getopt.GetoptError:
      print ('test.py -d YYYY-MM-DD')
      sys.exit(2)

   for opt, arg in opts:
      if opt == '-h':
         print ('test.py -date YYYY-MM-DD')
         sys.exit()
      elif opt in ("-d", "--date"):
         is_today = False
         show_date = arg

   print ('Show date: {}'.format(show_date))

# converts HH:MM to seconds into the day.
def emit_line(line):
    out_file.write(line + '\n')
    #print(line)

def get_rltime(time_str):
    hours = time_str[0:2]
    minutes = time_str[2:4]
    rltime = int(hours) * 3600 + int(minutes) * 60
    return rltime

def emit_zootopia_start_timed(time_str):
    rl_time = get_rltime(time_str)
    emit_line(START_ZOOTOPIA_TIMED.format(rl_time))

def emit_zootopia_start():
    emit_line(START_ZOOTOPIA)

def emit_autodj_start(time_str):
    START_AUTODJ = SILENCE_FILE + '	squeeze	{0}			file://' + RLDJ_SCRIPTS + 'AutodjOn.applescript			Autodj - on'
    rl_time = get_rltime(time_str)
    emit_line(START_AUTODJ.format(rl_time))

def emit_zootopia_end(time_str):
    rl_time = get_rltime(time_str)
    emit_line(STOP_ZOOTOPIA.format(rl_time))

def emit_break(time_str):
    rl_time = get_rltime(time_str)
    emit_line(START_BREAK.format(rl_time))

def emit_LID():
    # this file should have 1 second of lead silence becasuse of the delay
    # incurred when switching from Zootopia to AutoDJ.
    lid_file = SPOTBOX_PATH + '/LID_KZSU_Guy.mp3'
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
            print(" add: " + add_item)
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
        print("Execute: {} returned {}, {}".format(cmd, ret_val[0], ret_val[1]))
        if ret_val[1] and ret_val[1].find("Duration:") > 0:
            time_str = ret_val[1]
            idx1 = time_str.index('Duration:') + 9
            idx2 = time_str.index(',', idx1)
            time_str = time_str[idx1:idx2].strip()
            time = datetime.datetime.strptime(time_str, '%H:%M:%S.%f')
            duration = time.second + time.minute * 60 + time.hour * 3600
    except:
        print('Could not get duration for: ' + filePath)

    return duration

parse_args(sys.argv[1:])
shows_path = UPLOAD_DIR + show_date + "*.mp3"
show_day = datetime.datetime.strptime(show_date, '%Y-%m-%d').strftime('%A')
is_weekend = show_day == 'Saturday' or show_day == 'Sunday'
is_sunday = show_day == 'Sunday'
out_file = open('{}/{}.rlprg'.format(UPLOAD_DIR,show_day), "w");
run_time = datetime.datetime.now().time()

print('shows for {0}, {1}'.format(show_date, show_day))
shows = glob.glob(shows_path)
if len(shows) == 0:
    print('No shows for ' + shows_path)
    sys.exit(1)

add_extras_for_day(shows, show_day, show_date)
shows.sort()

# TODO - get actual durations
emit_line('Duration:19807')

#TODO - handle no shows case

prev_end_time = False
prev_silence = False
is_first = True
for show_line in shows:
    show = ShowInfo(show_line)
    show_title = show.title
    start_time = show.start_time
    end_time = show.end_time
    length_mins = int(end_time) - int(start_time)

    # skip this check for shows after midnight (KZSU time)
    is_valid_time = int(start_time) < 2400
    if is_today and is_valid_time:
        start_time_obj = datetime.datetime.strptime(start_time, '%H%M').time()
        if start_time_obj < run_time:
            print("skip past show: " + show_title)
            continue

    block_start_time = start_time

    if is_first or (prev_end_time and prev_end_time != block_start_time):
        if prev_end_time:
            emit_zootopia_start()

        emit_zootopia_end(block_start_time)

    if start_time.endswith('00'):
        emit_LID()

    emit_program_play(show_line, show_title)

    # skip this check if show start >= midnight or if start and end times are equal
    if is_valid_time and length_mins > 2:
        schedule_duration = get_schedule_duration(start_time, end_time)
        file_duration = get_mp3_duration(show_line)
        needs_correction = file_duration > 0 and abs(schedule_duration - file_duration) > 10
        if needs_correction:
            if file_duration < schedule_duration:
                emit_program_play(OUTRO_FILE, "outro")

            emit_break(end_time)

    is_first = False
    prev_end_time = end_time

# reenable Zootopia
emit_zootopia_start()

out_file.close()



