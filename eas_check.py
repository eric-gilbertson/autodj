#!/usr/bin/env python3
"""Check file for EAS alerts by looking for a 1050Hz tone.

"""
import argparse, time, math, os, subprocess, datetime, glob
from calendar import monthrange
import sounddevice as sd
import soundfile as sf

ARCHIVE_PATH = '/Volumes/Public/kzsu-aircheck-archives'
ARCHIVE_PATH = '/media/pr2100/kzsu-aircheck-archives'


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

def save_tone_segment(srcPath, timeSecs):
    fileName = os.path.basename(srcPath)
    startSecs = max(0, timeSecs - 30)
    outPath = '/tmp/eas_hit-{}-{:02d}{:02d}.wav'.format(fileName[0:-4], math.floor(timeSecs/60), math.floor(timeSecs %60))
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
def eas_tone_check(audioFile, toneLengthSecs):
    TARGET_FREQ=1580
    GAP_MIN=21
    GAP_MAX=25
    CHANNEL = 1

    wavFile = audioFile
    deleteFile = False
    if (audioFile.endswith('.mp3')):
        wavFile = make_wav_file(audioFile)
        deleteFile = True

    block, sampleRate = sf.read(wavFile)
    if sampleRate != 44100 and sampleRate != 48000:
        print("Unsupported sample rate") # this probably works but haven't tested it
        return 0

    file = sf.SoundFile(wavFile, 'r')
    minHits = (sampleRate  * toneLengthSecs) / TARGET_FREQ
    samplePeriod = 1.0 / sampleRate

    isIncreasing = None
    prevVal = False
    prevMaxIdx = 0
    prevMinIdx = 0
    idx = -1
    hitCnt = 0
    hitVal = 0
    while file.tell() < file.frames:
        pos = file.tell()
        block = file.read(1024*1024)
        if isIncreasing == None:
            prevVal = block[0][CHANNEL]
            isIncreasing = block[1][CHANNEL] > block[0][CHANNEL]

        for pair in block:
            #print("compoare: {}, {}".format(prev0, pair[0]))
            if isIncreasing and prevVal > 0 and (pair[CHANNEL] < prevVal):
                delta = idx - prevMaxIdx
                #print("delta: {}".format(delta))
                if GAP_MIN <= delta <= GAP_MAX:
                    #print("hit: {}, {}".format(sampleCnt, idx*samplePeriod))
                    hitCnt += 1
                    hitVal +=  pair[CHANNEL]
                else:
                    #print("reset sampleCnt {}, {}".format(delta, hitCnt))
                    hitCnt = 0
                    hitVal = 0

                if hitCnt > minHits:
                    avgVal = hitVal / hitCnt
                    #print("avg value: {}".format(avgVal))

                    if avgVal >= 0.1:
                        print("avg value: {}".format(avgVal))
                        hitTime = idx * samplePeriod
                        save_tone_segment(wavFile, hitTime)
                        return idx * samplePeriod
                    else:
                        #print("avg value tooclows: {}".format(avgVal))
                        hitCnt = 0
                        hitVal = 0

                prevMaxIdx = idx
                isIncreasing = False
            elif isIncreasing == False and prevVal < 0 and (pair[CHANNEL] > prevVal):
                prevMinIdx = idx
                isIncreasing = True

            prevVal = pair[CHANNEL]
            idx += 1

#    if deleteFile and wavFile != audioFile:
#        os.remove(wavFile)

    #print("hits: {}, {}".format(hitCnt, idx))
    return -1

def check_file(filePath):
    #print("check file: " + filePath)
    easTimeSecs = eas_tone_check(filePath, .5)

    if easTimeSecs == 0:
        print("{}: check failed.".format(filePath))
    elif easTimeSecs > 0:
        print("{}: tone at {} seconds ({:02d}:{:02d})".format(filePath, math.floor(easTimeSecs),
                                                              math.floor(easTimeSecs / 60),
                                                              math.floor(easTimeSecs % 60)))
    else:
        print("{}: okay".format(os.path.basename(filePath)))

def process_day(year, month, day, hour):
    log_it("Process day {}, {}, {}, {}".format(year, month, day, hour))
    files = get_src_files(year, month, day, hour)

    if len(files) == 0:
        log_it("no files for: {}-{}-{}:{}".format(year, month, day, hour))
        return
    else:
        for file in files:
            check_file(file)

def process_month(year, month):
    log_it("Process month {}, {}".format(year, month))
    num_days = monthrange(year, month)[1]
    for day in range(num_days):
        log_it('process day: ' + str(day+1))
        process_day(year, month, day+1, -1)

def process_year(year):
    log_it("Process year {}".format(year))
    for month in range(12):
        log_it("process month: {}".format(month+1))
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
    date = datetime.datetime.strptime(args.datetime, '%Y-%m-%d%H%M')
    process_day(date.year, date.month, date.day, date.hour)
else:
    log_it("Invalid date: " + args.date)


