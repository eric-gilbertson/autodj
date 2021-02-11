##!/usr/bin/python

import datetime, sys, getopt, os
from array import *
import glob
import urllib
import commands

GDRIVE_PATH = '/Volumes/GoogleDrive/My Drive'
KZSU_NEWS_PATH = '/Volumes/GoogleDrive/My Drive/show submissions/Ken Der News'
#GDRIVE_PATH = '/Users/Barbara/GoogleDrive/My Drive'

SILENCE_FILE = '	file:///Volumes/GoogleDrive/My%20Drive/show_uploads/silence.aiff'
OUTRO_FILE = '/Volumes/GoogleDrive/My Drive/show_uploads/show_fill.mp3'

SPOTBOX_PATH = GDRIVE_PATH + '/spotbox audio/'

START_BREAK = SILENCE_FILE + '	false	{0}						Time Break'
START_AUTODJ = SILENCE_FILE + '	squeeze	{0}			file:///Users/engineering/Music/Radiologik/Scripts/AutodjOn.applescript			Autodj - on'
START_ZOOTOPIA_TIMED = SILENCE_FILE + '	false	{0}		file:///Users/engineering/Music/Radiologik/Scripts/ZootopiaOn.applescript				ZootopiaInt - on'
START_ZOOTOPIA = SILENCE_FILE + '	false	-1			file:///Users/engineering/Music/Radiologik/Scripts/ZootopiaOn.applescript			Zootopia - on'
PLAY_PROGRAM  = '	file://{}	false	-1					{}'

UPLOAD_DIR = GDRIVE_PATH + '/show_uploads/'

day_extras = {
    'Sunday' : [],
    'Monday' : [],
    'Tuesday' : [],
    'Wednesday' : [],
    'Thursday' : [],
    'Friday' : [],
    'Saturday' : [],
}

is_today = True
run_immediate = False

show_date = datetime.datetime.now().strftime("%Y-%m-%d")

def parse_args(argv):
   global show_date, is_today

   try:
      opts, args = getopt.getopt(argv,"d:",["date"])
   except getopt.GetoptError:
      print 'test.py -d YYYY-MM-DD'
      sys.exit(2)

   for opt, arg in opts:
      if opt == '-h':
         print 'test.py -date YYYY-MM-DD'
         sys.exit()
      elif opt in ("-d", "--date"):
         is_today = False
         show_date = arg

   print 'Show date: "', show_date

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
    rl_time = get_rltime(time_str)
    emit_line(START_AUTODJ.format(rl_time))

def emit_break(time_str):
    rl_time = get_rltime(time_str)
    emit_line(START_BREAK.format(rl_time))

def emit_LID():
    lid_file = GDRIVE_PATH + '/spotbox audio/LID_0.02_Standard LID_The "KZSU Guy"_Official_2004 __.wav'
    emit_program_play(lid_file, "LID")

def emit_program_play(show_file, show_title):
    show_file_encoded = urllib.quote(show_file)
    play_line = PLAY_PROGRAM.format(show_file_encoded, show_title)
    emit_line(play_line)

def emit_kzsu_news(show_file):
    short_date = datetime.datetime.strptime(show_date, '%Y-%m-%d').strftime('%m%d')
    news_path = '{}/{}-0900,1200,1700 Ken Der News.mp3'.format(KZSU_NEWS_PATH, short_date)
    news_file_encoded = urllib.quote(news_path)
    play_line = PLAY_PROGRAM.format(news_file_encoded, 'KZSU News')
    emit_line(play_line)

def get_news_start_time_for_time(end_time_str):
    news_times = [['0900', '0905'], ['1200', '1205'], ['1700', '1705']]
    for news_time in news_times:
        if end_time_str == news_time[1]:
            return news_time[0]

    return False

def add_extras_for_day(shows, day_ord, date_str):
    extras = day_extras[day_ord]
    for extra in extras:
        add_item = '{}{}{}'.format(UPLOAD_DIR, date_str, extra)
        print(" add: " + add_item)
        shows.append(add_item) ######

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
out_file = open('{}/{}.rlprg'.format(UPLOAD_DIR,show_day), "w");
run_time = datetime.datetime.now().time()
#TODO check for newscast time if weekday and abort

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
is_first = True
for show in shows:
    file_name = show[len(UPLOAD_DIR):]
    print("show: " + file_name);
    info_ar = file_name.split('_')
    show_title = info_ar[2]
    time_ar = info_ar[1].split('-')
    start_time = time_ar[0]
    end_time = time_ar[1]

    # skip this check for shows after midnight (KZSU time)
    is_valid_time = int(start_time) < 2400
    if is_today and is_valid_time:
        start_time_obj = datetime.datetime.strptime(start_time, '%H%M').time()
        if start_time_obj < run_time:
            print("skip past show: " + show_title)
            continue

    news_start_time = get_news_start_time_for_time(start_time) if not is_weekend else False
    block_start_time = news_start_time if news_start_time else start_time

    if is_first or (prev_end_time and prev_end_time != block_start_time):
        if prev_end_time:
            emit_zootopia_start()

        emit_autodj_start(block_start_time)

    if news_start_time:
        emit_LID()
        emit_kzsu_news(news_start_time)
        prev_end_time = start_time

    if start_time.endswith('00'):
        emit_LID()

    emit_program_play(show, show_title)

    # skip this check if show start >= midnight
    if is_valid_time:
        schedule_duration = get_schedule_duration(start_time, end_time)
        file_duration = get_mp3_duration(show)
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



