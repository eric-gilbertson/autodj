import os, subprocess, sys, datetime

# return time length in seconds of an mp3 file using ffmpeg or -1 if invalid.
# assumes user has ffmpeg in PATH.
def execute_ffmpeg_command(cmd):
    cmd = "/usr/local/bin/ffmpeg -hide_banner " + cmd
    print("Execute: {}".format(cmd))
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    (output, err) = p.communicate()
    p_status = p.wait()
    err = str(err)

    print("Execute: returned {}, {}".format(output, err))
    return p_status

def get_mp3_duration(filePath):
    duration = -1
    cmd = "/usr/local/bin/ffmpeg -hide_banner -i '" + filePath + "'"
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    (output, err) = p.communicate()
    p_status = p.wait()
    err = str(err)

    print("Execute: {} returned {}, {}".format(cmd, output, err))
    if err.find("Duration:") > 0:
        time_str = err
        idx1 = time_str.index('Duration:') + 9
        idx2 = time_str.index(',', idx1)
        time_str = time_str[idx1:idx2].strip()
        time = datetime.datetime.strptime(time_str, '%H:%M:%S.%f')
        duration = time.second + time.minute * 60 + time.hour * 3600

    is_44100Hz = err.find('44100 Hz') > 0
    return (duration, is_44100Hz)


def insert_disclaimer(srcFile, fileDurationMins):
    retFile = None
    INSERT_GAP = 30*60 #seconds
    TMP_PATH = 'disclaimer_file'
    retFile = None
    (durationSeconds, is44100Hz) = get_mp3_duration(srcFile)

    if durationSeconds < 0:
        return retFile    

    startTime = 0
    fileCnt = 0
    while startTime < durationSeconds:
        endTime = startTime + min(INSERT_GAP, durationSeconds - startTime)
        tmpFile = TMP_PATH + str(fileCnt) + '.mp3'
        cmd = '-y  -i "{}" -ss {} -to {} -c:a copy {}'.format(srcFile, startTime, endTime, tmpFile)
        if execute_ffmpeg_command(cmd) != 0:
            return None

        startTime = endTime
        fileCnt = fileCnt + 1


    cmd = '-y -i "concat:'
    sepChar = ''
    disclaimFile = 'disclaimer44100.mp3' if is44100Hz else 'disclaimer48000.mp3'
    for i in range(fileCnt):
        cmd = cmd + '{}{}|{}{}.mp3'.format(sepChar, disclaimFile, TMP_PATH, i)
        sepChar = '|'

    metaTitle = os.path.basename(srcFile)[0:-4]
    destFile = srcFile[0:-4] + '_disclaim.mp3'
    cmd = cmd + '" -acodec copy -t {} -metadata title="{}" "{}"'.format(fileDurationMins*60, metaTitle, destFile)
    if execute_ffmpeg_command(cmd) == 0:
        retFile = destFile
    elif os.path.exists(destFile):
        os.rename(destFile, destFile + ".bad")

    return retFile



if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: ffmpeg_utils <FILE_NAME>")
    else:
        srcFile = sys.argv[1]
        disclaimFile = insert_disclaimer(srcFile, 60)
        print("Result file : {}".format(disclaimFile))
