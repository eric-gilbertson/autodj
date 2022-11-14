#!/usr/bin/env python3
"""Write mp3 stream to hourly files.

"""
import time, math, os, subprocess, datetime, glob

STREAM_URL='http://kzsu-streams.stanford.edu/kzsu-1-128.mp3'
ARCHIVE_PATH = '/media/pr2100/kzsu-aircheck-archives'
SEGMENT_MINUTES = 60


def log_it(msg):
   print(msg, flush=True)

def make2digit(some_int):
    res = "{:02d}".format(some_int)
    return res

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

def record_segment():
    now = datetime.datetime.now()
    offset_seconds  = (now - now.replace(minute=0, second=0, microsecond=0)).total_seconds()
    segment_seconds = SEGMENT_MINUTES * 60 - offset_seconds
    minutes = math.floor(segment_seconds / 60)
    seconds = "{:.2f}".format(segment_seconds % 60)
    segment_file = now.strftime('kzsu-%Y-%m-%d-%H00.mp3.tmp')
    cmd = '-i {} -c copy -t 00:{}:{} {}'.format(STREAM_URL, minutes, seconds, segment_file)
    log_it("cmd: " + cmd)
    return
    execute_ffmpeg_command(cmd)



record_segment()

#while True:
#    record_segment()


