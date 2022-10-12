#!/usr/bin/env python3
"""Check file for EAS alerts by looking for a 1050Hz tone.

"""
import argparse, time, math, os, subprocess, datetime, glob
from calendar import monthrange
import sounddevice as sd
import soundfile as sf

ARCHIVE_PATH = '/Volumes/Public/kzsu-aircheck-archives'
#ARCHIVE_PATH = '/media/pr2100/kzsu-aircheck-archives'



parser = argparse.ArgumentParser(add_help=False)
parser.add_argument(
    '-l', '--list-devices', action='store_true',
    help='show list of audio devices and exit')
args, remaining = parser.parse_known_args()

if args.list_devices:
    print(sd.query_devices())
    parser.exit(0)
parser = argparse.ArgumentParser(
    description=__doc__,
    formatter_class=argparse.RawDescriptionHelpFormatter,
    parents=[parser])
parser.add_argument(
    '-filename', metavar='FILENAME',
    help='audio file to be played back')
parser.add_argument(
    '-date', metavar='DATE',
    help='Archive date to check')
parser.add_argument(
    '-datetime', metavar='DATE',
    help='Archive date to check')

args = parser.parse_args(remaining)

def log_it(msg):
   print(msg, flush=True)

def make2digit(some_int):
    res = "{:02d}".format(some_int)
    return res

def get_src_files(year, month, day, hour):
    months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
    hour2d = make2digit(hour) + '00' if hour >= 0 else '*'
    filename = 'kzsu-{}-{}-{}-{}.mp3'.format(year, make2digit(month), make2digit(day), hour2d)
    path = '{}/{}/{}/{}/{}'.format(ARCHIVE_PATH, year,  months[month-1], make2digit(day), filename)
    #print("path: " + path)
    files = glob.glob(path)
    return files

def execute_ffmpeg_command(cmd):
    cmd = "/usr/local/bin/ffmpeg -hide_banner " + cmd
    #print("Execute: {}".format(cmd))
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    (output, err) = p.communicate()
    p_status = p.wait()
    err = str(err)

    if p_status != 0:
        print("Execute: returned {}, {}".format(output, err))

    return p_status

# returns array of silence gaps with start/end times
def find_silence_gaps(filePath):
    gaps = []
    duration = -1
    cmd = '/usr/local/bin/ffmpeg -hide_banner -i "{}"  -af silencedetect=n=-30dB:d=0.8 -f null -'.format(filePath)
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    (output, err) = p.communicate()
    p_status = p.wait()
    result = str(err, 'utf-8')

    duration = -1
    if result.find("Duration:") > 0:
        idx1 = result.find('Duration:') + 9
        idx2 = result.find(',', idx1)
        time_str = result[idx1:idx2].strip()
        time = datetime.datetime.strptime(time_str, '%H:%M:%S.%f')
        duration = time.second + time.minute * 60 + time.hour * 3600

    silence_start_idx = result.find('silence_start: ') + 15
    while silence_start_idx > 15:
        silence_start_idx2 = result.find('\n', silence_start_idx)
        start_time = result[silence_start_idx:silence_start_idx2]
        start_time = float(start_time)
        silence_end_idx = result.find('silence_end: ', silence_start_idx) + 13
        silence_end_idx2 = result.find('|', silence_end_idx)
        end_time = result[silence_end_idx:silence_end_idx2]
        end_time = float(end_time)
        gaps.append([start_time, end_time, end_time - start_time])
        silence_start_idx = result.find('silence_start: ', silence_start_idx) + 15

    return (duration, gaps)


def save_tone_segment(srcPath, timeSecs):
    notUsed, fileSuffix = os.path.splitext(srcPath)
    fileName = os.path.basename(srcPath)[0:-4]
    startSecs = max(0, timeSecs - 15)
    outPath = '/tmp/eas_hit-{}-{:02d}{:02d}{}'.format(fileName, math.floor(timeSecs/60), math.floor(timeSecs %60), fileSuffix)
    cmd = '-y  -i "{}" -ss {} -to {} -c:a copy "{}"'.format(srcPath, startSecs, startSecs+60, outPath)
    execute_ffmpeg_command(cmd)

def make_wav_file(audioFile):
    retVal = None
    wavFile = '/tmp/' + os.path.basename(audioFile)[0:-4] + '.wav'
    cmd = '-y -i "{}" "{}"'.format(audioFile, wavFile)
    if execute_ffmpeg_command(cmd) == 0:
        retVal = wavFile
    else:
        print("Error creating wav file for: " + audioFile)

    return retVal

def seconds_to_time(seconds):
    mins = math.floor(endTimeSecs / 60)
    secs = math.floor(endTimeSecs % 60)
    timeStr = '{:02d}:{:02d}'.format(min, secs)
    return timeStr


# check for a 1050Hz tone of toneLengthSecs and return the time point
# (in seconds) if found, else -1 or 0 if error
def eas_check(audioFile):
    MAX_MSG_TIME = 120
    (durationSecs, gaps) = find_silence_gaps(audioFile)
    if len(gaps) == 0:
        log_it("No gaps: " + audioFile)
        return (-1, -1) # probably an error

    startToneTime = 0
    while (startToneTime) >= 0:
        (startToneStart, startToneEnd) = find_tone_burst(startToneTime, gaps, durationSecs)
        if startToneStart > 0:
            (endToneStart, endToneEnd) = find_tone_burst(startToneEnd, gaps, durationSecs)
            isFileEnd = durationSecs - startToneStart < 60
            isTonePair = endToneEnd > 0 and endToneEnd - startToneStart < 120

            if isFileEnd or isTonePair:
                # save iff an hour file from the archive, e.g. not for test files
                if audioFile.startswith(ARCHIVE_PATH) and durationSecs > 50*60:
                    save_tone_segment(audioFile, startToneStart)

                return (startToneStart, endToneEnd)
            else:
                log_it("False start hit at {}".format(seconds_to_time(startToneStart)))

    return (-1, -1)


def find_tone_burst(startCheckTime, gaps, duration_secs):
    TONE_END_MAX_GAP = 60
    SILENCE_MIN = 0.9
    SILENCE_MAX = 1.2

    TONE_MIN = 0.2
    TONE_MAX = 2.0
#    if longBurst == False:
#        TONE_MIN = 0.2
#        TONE_MAX = 0.5

    idx = 0;
    prevGapAr = gaps[0]
    prevToneLen = prevPrevTone = 12341431
    prevGapStart = prevPrevGapStart = prevPrevPrevGapStart = 3434234
    prevPrevGapLen = prevGapLen = 13412343
    prevPrevGapEnd = prevGapEnd = 2341234
    for idx in range(len(gaps)):
        gapAr = gaps[idx]
        if gapAr[0] < startCheckTime:
            continue
        #print("gap: {}, {}".format(gapAr[2], nextGapAr[2]))
        gapLen = gapAr[2]
        toneLen = gapAr[0] - prevGapAr[1]
        atEnd = duration_secs - gapAr[0] < 5
        if atEnd and TONE_MIN < toneLen < TONE_MAX and SILENCE_MIN <= gapLen <=SILENCE_MAX:
            return (gapAr[0], gapAr[1])
        elif SILENCE_MIN < gapLen < TONE_END_MAX_GAP and \
           SILENCE_MIN < prevGapLen < SILENCE_MAX and \
           SILENCE_MIN < prevPrevGapLen and \
           TONE_MIN <= toneLen < TONE_MAX and \
           TONE_MIN <= prevToneLen < TONE_MAX  and \
           TONE_MIN <= prevPrevToneLen < TONE_MAX:
            return (prevPrevPrevGapStart, gapAr[1])

        prevPrevPrevGapStart = prevPrevGapStart
        prevPrevToneLen = prevToneLen
        prevPrevGapStart = prevGapStart
        prevToneLen = toneLen
        prevGapStart = gapAr[0]
        prevPrevGapLen = prevGapLen
        prevGapLen = gapLen
        prevPrevGapEnd = prevGapEnd
        prevGapEnd = prevGapAr[1]
        prevGapAr = gapAr
        idx += 1

    return (-1, -1)

def check_file(filePath):
    #print("check file: " + filePath)
    (startToneStart, endToneEnd) = eas_check(filePath)
    fileName = os.path.basename(filePath)

    if startToneStart == 0:
        print("{}: check failed.".format(fileName))
    elif startToneStart > 0:
        #assume end of file if -1
        endToneEnd = endToneEnd if endToneEnd >= 0 else 3600 - 1
        log_it("{}, {} - {}, tone ({:.1f})".format(fileName, startToneStart, endToneEnd, endToneEnd - startToneStart))
    else:
        log_it("{}: okay".format(os.path.basename(fileName)))

def process_day(year, month, day, hour):
    #log_it("Process day {}, {}, {}, {}".format(year, month, day, hour))
    files = get_src_files(year, month, day, hour)

    if len(files) == 0:
        #log_it("no files for: {}-{}-{}:{}".format(year, month, day, hour))
        return
    else:
        for file in files:
            check_file(file)

def process_month(year, month):
    #log_it("Process month {}, {}".format(year, month))
    num_days = monthrange(year, month)[1]
    for day in range(num_days):
        #log_it('process day: ' + str(day+1))
        process_day(year, month, day+1, -1)

def process_year(year):
    #log_it("Process year {}".format(year))
    for month in range(12):
        #log_it("process month: {}".format(month+1))
        process_month(year, month+1)


if args.filename:
    check_file(args.filename)
elif args.date:
    date_ar = args.date.split('-')
    date_len = len(date_ar)

    if date_len == 1:
        process_year(int(date_ar[0]))
    elif date_len == 2:
        process_month(int(date_ar[0]), int(date_ar[1]))
    elif date_len == 3:
        process_day(int(date_ar[0]), int(date_ar[1]), int(date_ar[2]), -1)
elif args.datetime:
    date = datetime.datetime.strptime(args.datetime, '%Y-%m-%d-%H%M')
    process_day(date.year, date.month, date.day, date.hour)
else:
    log_it("Invalid date: " + args.date)


