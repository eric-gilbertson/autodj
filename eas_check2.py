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
    result = str(err)

    silence_start_idx = result.find('silence_start: ') + 15
    while silence_start_idx > 15:
        silence_start_idx2 = result.find('\\n', silence_start_idx)
        start_time = result[silence_start_idx:silence_start_idx2]
        start_time = float(start_time)
        silence_end_idx = result.find('silence_end: ', silence_start_idx) + 13
        silence_end_idx2 = result.find('|', silence_end_idx)
        end_time = result[silence_end_idx:silence_end_idx2]
        end_time = float(end_time)
        gaps.append([start_time, end_time, end_time - start_time])
        silence_start_idx = result.find('silence_start: ', silence_start_idx) + 15

    return gaps


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


# check for a 1050Hz tone of toneLengthSecs and return the time point
# (in seconds) if found, else -1 or 0 if error
def eas_check(audioFile):
    MAX_MSG_TIME = 120
    gaps = find_silence_gaps(audioFile)
    if len(gaps) == 0:
        log_it("No gaps: " + audioFile)
        return (-1, -1) # probably an error

    startToneTime = find_tone_burst(0, True, gaps)
    if startToneTime > 0:
        endToneTime = find_tone_burst(startToneTime, False, gaps)

        if endToneTime > 0 and endToneTime - startToneTime <= MAX_MSG_TIME:
            return (startToneTime, endToneTime)
        else:
            log_it("No end tone found.")

    return (-1, -1)


def find_tone_burst(startCheckTime, longBurst, gaps):
    MSG_START_MAX_GAP = 10
    SILENCE_MIN = 0.9
    SILENCE_MAX = 1.2

    TONE_MIN = 0.8
    TONE_MAX = 2.0
    if longBurst == False:
        TONE_MIN = 0.2
        TONE_MAX = 0.4

    idx = 0;
    prevGapAr = gaps[0]
    prevToneLen = prevPrevTone = 12341431
    prevPrevGapLen = prevGapLen = 13412343
    for idx in range(len(gaps)):
        gapAr = gaps[idx]
        if gapAr[0] < startCheckTime:
            continue
        #print("gap: {}, {}".format(gapAr[2], nextGapAr[2]))
        gapLen = gapAr[2]
        toneLen = gapAr[0] - prevGapAr[1]
        if SILENCE_MIN < gapLen < MSG_START_MAX_GAP and \
           SILENCE_MIN < prevGapLen < SILENCE_MAX and \
           SILENCE_MIN < prevPrevGapLen and \
           TONE_MIN <= toneLen < TONE_MAX and \
           TONE_MIN <= prevToneLen < TONE_MAX  and \
           TONE_MIN <= prevPrevToneLen < TONE_MAX:
            hitTime = gapAr[0]
            #print("hit: {:02f}, {:02f}, {:02f}, {:02f}, {:02f}, {:02f}, {:02f}".format(prevPrevGapLen, prevPrevToneLen, prevGapLen, prevToneLen, toneLen, gapLen, hitTime))
            return hitTime

        prevPrevToneLen = prevToneLen
        prevToneLen = toneLen
        prevPrevGapLen = prevGapLen
        prevGapLen = gapLen
        prevGapAr = gapAr
        idx += 1

    return -1

def check_file(filePath):
    #print("check file: " + filePath)
    (startTimeSecs, endTimeSecs) = eas_check(filePath)

    if startTimeSecs == 0:
        print("{}: check failed.".format(filePath))
    elif startTimeSecs > 0:
        save_tone_segment(filePath, startTimeSecs)
        log_it("{}: tone at {}-{} seconds ({:02d}:{:02d})".format(filePath, math.floor(startTimeSecs), math.floor(endTimeSecs),
                                                              math.floor(startTimeSecs / 60),
                                                              math.floor(startTimeSecs % 60)))
    else:
        log_it("{}: okay".format(os.path.basename(filePath)))

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


