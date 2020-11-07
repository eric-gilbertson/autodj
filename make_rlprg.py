##!/usr/bin/python

import datetime, sys, getopt, os
from array import *
import glob
import urllib
import commands

GDRIVE_PATH = '/Volumes/GoogleDrive/My Drive'
#GDRIVE_PATH = '/Users/Barbara/GoogleDrive/My Drive'

SILENCE_FILE = '	file:///Volumes/GoogleDrive/My%20Drive/show_uploads/silence.aiff'

SPOTBOX_PATH = GDRIVE_PATH + '/spotbox audio/'

START_BREAK = SILENCE_FILE + '	false	{0}						Time Break'
STOP_ZOOTOPIA = SILENCE_FILE + '	false	{0}	2					Zootopia - off'
START_ZOOTOPIA = SILENCE_FILE + '	false	{0}	1					Zootopia - on'
PLAY_PROGRAM  = '	file://{}	false	-1					{}'

UPLOAD_DIR = GDRIVE_PATH + '/show_uploads/'

SILENCE_TRACK="SilenceTrack.mp3"
#UPW_INTRO_TRACK= SPOTBOX_PATH + 'UPW Intro 2020.mp3'
#UPW_OUTO_TRACK= SPOTBOX_PATH + 'UPW Outro 2020.mp3'
UPW_INTRO_TRACK= 'UPW Intro 2020.mp3'
UPW_OUTO_TRACK= 'UPW Outro 2020.mp3'
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

def emit_zootopia_start(time_str):
    rl_time = get_rltime(time_str)
    emit_line(START_ZOOTOPIA.format(rl_time))

def emit_zootopia_end(time_str):
    rl_time = get_rltime(time_str)
    emit_line(STOP_ZOOTOPIA.format(rl_time))

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

def is_news_show(start_time_str, end_time_str):
    news_times = [['0900', '0905'], ['1200', '1205'], ['1700', '1705']]
    for news_time in news_times:
        if start_time == news_time[0] and end_time == news_time[1]:
            return True

    return False

def add_extras_for_day(shows, day_ord, date_str):
    extras = day_extras[day_ord]
    for extra in extras:
        add_item = '{}{}{}'.format(UPLOAD_DIR, date_str, extra)
        print(" add: " + add_item)
        shows.append(add_item) ######


parse_args(sys.argv[1:])
shows_path = UPLOAD_DIR + show_date + "*.mp3"
show_day = datetime.datetime.strptime(show_date, '%Y-%m-%d').strftime('%A')
is_weekend = show_day != 'Saturday' and show_day != 'Sunday'
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

prev_end_time = ''
is_first = True
for show in shows:
    file_name = show[len(UPLOAD_DIR):]
    print("show: " + file_name);
    info_ar = file_name.split('_')
    show_title = info_ar[2]
    time_ar = info_ar[1].split('-')
    start_time = time_ar[0]
    end_time = time_ar[1]
    is_silent = show_title == SILENCE_TRACK

    # skip this check for shows after midnight (KZSU time)
    if is_today and int(start_time) <= 2400:
        start_time_obj = datetime.datetime.strptime(start_time, '%H%M').time()
        if start_time_obj < run_time:
            print("skip past show: " + show_title)
            continue

    if is_first:
        emit_zootopia_end(start_time)

    if not is_weekend and is_news_show(start_time, end_time):
        emit_zootopia_start(start_time)
    else:
        if not is_first and not prev_silent and prev_end_time != start_time:
            emit_zootopia_start(prev_end_time)
            emit_zootopia_end(start_time)
        elif not is_first:
            emit_break(start_time)

        if not is_silent:
            if start_time.endswith('00'):
                emit_LID()

            emit_program_play(show, show_title)

    is_first = False
    prev_end_time = end_time
    prev_silent = is_silent

# reenable Zootopia
emit_zootopia_start(end_time)

out_file.close()



