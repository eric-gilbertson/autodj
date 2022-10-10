#!/usr/bin/python
#
# removes a chunk from an audio file between startTime and endTime and writes
# it to <INPUT_FILE>.clean
#
import os, subprocess, sys, datetime, math, pathlib

ARCHIVE_PATH = '/Volumes/Public/kzsu-aircheck-archives'
#ARCHIVE_PATH = '/media/pr2100/kzsu-aircheck-archives'
#ARCHIVE_PATH = '/Users/Barbara/tmp/kzsu-archive'

CLEAN_SUFFIX = ".clean.mp3"

def log_it(msg):
   print(msg, flush=True)

# return time length in seconds of an mp3 file using ffmpeg or -1 if invalid.
# assumes user has ffmpeg in PATH.
def execute_ffmpeg_command(cmd):
    cmd = "/usr/local/bin/ffmpeg -hide_banner " + cmd
    #print("Execute: {}".format(cmd))
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    (output, err) = p.communicate()
    p_status = p.wait()
    err = str(err)

    if p_status != 0:
        print("Error execute: returned {}, {}".format(output, err))

    return p_status

def save_audio_segment(srcPath, timeSecs):
    fileName = os.path.basename(srcPath)
    fileSuffix = pathlib.Path(fileName).suffix
    startSecs = max(0, timeSecs - 15)
    outPath = '/tmp/eas_clean-{}-{:02d}{:02d}{}'.format(fileName[0:-4], math.floor(timeSecs/60), math.floor(timeSecs %60), fileSuffix)
    cmd = '-y  -i "{}" -ss {} -to {} -c:a copy "{}"'.format(srcPath, startSecs, startSecs+30, outPath)
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

def remove_chunk(srcFile, startTime, endTime):
    tmp1 = '/tmp/segment_extract1.mp3'
    tmp2 = '/tmp/segment_extract2.mp3'
    outFile = srcFile[0:-4] + CLEAN_SUFFIX

    if os.path.exists(outFile):
        os.remove(outFile)

    if os.path.exists(tmp1):
        os.remove(tmp1)

    if os.path.exists(tmp2):
        os.remove(tmp2)

    cmd = ' -y  -i "{}" -to {} -c:a copy {}'.format(srcFile, startTime, tmp1)
    if execute_ffmpeg_command(cmd) != 0 or not os.path.exists(tmp1):
        return False

    cmd = ' -y  -i "{}" -ss {} -c:a copy {}'.format(srcFile, endTime, tmp2)
    if execute_ffmpeg_command(cmd) != 0 or not os.path.exists(tmp2):
        return False

    cmd = ' -y -i "concat:{}|{}"  -acodec copy  "{}" '.format(tmp1, tmp2, outFile)
    if execute_ffmpeg_command(cmd) != 0 or not os.path.exists(outFile):
        return False

    return outFile


# reads from a file of format:
# <YYYY-MM-DD>-<HH:00M>, <START_TIME> - <END-TIME>, .....
#
# and removes the specified time segment from the file outputting it
# to <FILE_NAME>.clean.mp3. It then moves the original files into the
# eas_shows archive dir if none exits and then moves the clean file into
# the orginal name. to protect against possible errors the process is skipped
# if the time range exceeds 120 seconds.
def process_manifest(manifestFile):
    months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']

    with open(manifestFile) as file:
        while (line := file.readline().rstrip()):
            if line.startswith('#'):
                continue

            lineAr = line.split(',')
            audioFileTime = lineAr[0]
            timeAr = lineAr[1].split('-')
            startTime = datetime.datetime.strptime(timeAr[0].strip(), '%M:%S')
            endTime = datetime.datetime.strptime(timeAr[1].strip(), '%M:%S')
            cleanGap = (endTime - startTime).total_seconds()
            if cleanGap > 120 or cleanGap <= 10:
                log_it('Skipping {} due to improper gap {}'.format(srcFile, cleanGap))
                continue

            dateAr = audioFileTime.split('-')
            archiveFile = 'kzsu-{}.mp3'.format(audioFileTime)
            srcPath = '{}/{}/{}/{}/{}'.format(ARCHIVE_PATH, dateAr[0], months[int(dateAr[1]) - 1], dateAr[2], archiveFile)
            log_it("Clean it: {} - {}, {}".format(timeAr[0], timeAr[1], srcPath))
            cleanPath = remove_chunk(srcPath, timeAr[0], timeAr[1])
            if cleanPath:
                savePath = '{}/eas_shows/{}'.format(ARCHIVE_PATH, archiveFile)
                if not os.path.exists(savePath):
                    os.rename(srcPath, savePath)
                    
                os.rename(cleanPath, srcPath)
                cutStartTimeAr = timeAr[0].split(':')
                cutStartSeconds = int(cutStartTimeAr[0]) * 60 + int(cutStartTimeAr[1])
                save_audio_segment(srcPath, cutStartSeconds)
            else:
                log_it("Error: extraction failed {}".format(srcPath))




if __name__ == "__main__":
    argCnt = len(sys.argv) - 1
    if argCnt == 1:
        process_manifest(sys.argv[1])
    elif argCnt == 3:
        start = sys.argv[1]
        end = sys.argv[2]
        srcFile = sys.argv[3]

        if not os.path.exists(srcFile):
            print("Invalid file: " + srcFile)
        else:
            newFile = remove_chunk(srcFile, start, end)
            if newFile:
                print("File created: " + newFile)
                sys.exit(0)
            else:
                print("Error creating file")
                sys.exit(1)
    else:
        print("Usage: remove_chunk [<MANIFEST_FILE> | <START_TIME> <END_TIME>  <FILE_NAME>")
        sys.exit(1)

