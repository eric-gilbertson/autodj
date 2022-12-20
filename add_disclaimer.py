import os, subprocess, sys, datetime, math

# return time length in seconds of an mp3 file using ffmpeg or -1 if invalid.
# assumes user has ffmpeg in PATH.
def execute_ffmpeg_command(cmd):
    cmd = "/usr/local/bin/ffmpeg -hide_banner " + cmd
    #print("Execute: {}".format(cmd))
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    (output, err) = p.communicate()
    p_status = p.wait()
    err = str(err)

    #print("Execute: returned {}, {}".format(output, err))
    return p_status

def get_mp3_duration(filePath):
    duration = -1
    cmd = "/usr/local/bin/ffmpeg -hide_banner -i '" + filePath + "'"
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    (output, err) = p.communicate()
    p_status = p.wait()
    err = str(err)

    #print("Execute: {} returned {}, {}".format(cmd, output, err))
    if err.find("Duration:") > 0:
        time_str = err
        idx1 = time_str.index('Duration:') + 9
        idx2 = time_str.index(',', idx1)
        time_str = time_str[idx1:idx2].strip()
        time = datetime.datetime.strptime(time_str, '%H:%M:%S.%f')
        duration = time.second + time.minute * 60 + time.hour * 3600

    is_44100Hz = err.find('44100 Hz') > 0
    return (duration, is_44100Hz)


# splits file into chunks and then cat's it back together with a disclaimer between each
# chunk and fade out last 10 seconds.
def insert_disclaimer(srcFile, destFile):
    retFile = None
    FADE_SECONDS=10
    DISCLAIM_GAP_MINS = 30
    TMP_PATH = 'disclaimer_file'
    retFile = None
    (srcFileSeconds, is44100Hz) = get_mp3_duration(srcFile)
    durationSeconds = srcFileSeconds
    disclaimFile = 'disclaimer44100.mp3' if is44100Hz else 'disclaimer48000.mp3'
    (disclaimerSeconds, is44100Hz) = get_mp3_duration(disclaimFile)
    disclaimerCnt = math.floor(durationSeconds / (DISCLAIM_GAP_MINS * 60))
    durationSeconds -= disclaimerCnt * disclaimerSeconds

    if durationSeconds < 0:
        return retFile    

    startTime = 0
    fileCnt = 0
    # split source file into chunks. make the last one FADE_SECONDS long so that i can be faded quickly.
    while startTime < durationSeconds:
        endTime = startTime + min(DISCLAIM_GAP_MINS*60, durationSeconds - startTime)
        if endTime == durationSeconds and endTime - startTime > FADE_SECONDS:
            endTime -= FADE_SECONDS

        tmpFile = TMP_PATH + str(fileCnt) + '.mp3'
        cmd = '-y  -i "{}" -ss {} -to {} -c:a copy {}'.format(srcFile, startTime, endTime, tmpFile)
        if execute_ffmpeg_command(cmd) != 0:
            return None

        startTime = endTime
        fileCnt = fileCnt + 1


    # add fade to the last segment
    fadeSrcFile = '{}{}.mp3'.format(TMP_PATH, fileCnt - 1)
    fadeDestFile = TMP_PATH + 'fadeout.mp3'
    cmd = '-y -i {} -af "afade=t=out:st={}:d={}" {}'.format(fadeSrcFile, 0, FADE_SECONDS, fadeDestFile)
    if execute_ffmpeg_command(cmd) != 0:
        return None

    os.rename(fadeDestFile, fadeSrcFile)


    cmd = '-y -i "concat:'
    sepChar = ''
    for i in range(fileCnt):
        if i == fileCnt - 1:
            cmd = cmd + '|{}{}.mp3'.format(TMP_PATH, i)
        else:
            cmd = cmd + '{}{}|{}{}.mp3'.format(sepChar, disclaimFile, TMP_PATH, i)

        sepChar = '|'

    metaTitle = os.path.basename(srcFile)[0:-4]
    cmd = cmd + '" -acodec copy -t {} -metadata title="{}" "{}"'.format(srcFileSeconds, metaTitle, destFile)
    if execute_ffmpeg_command(cmd) == 0:
        retFile = destFile
    elif os.path.exists(destFile):
        os.rename(destFile, destFile + ".bad")

    return retFile



if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: {} <FILE_NAME>".format(sys.arvv[0]))
    else:
        srcFile = sys.argv[1]
        disclaimFile = srcFile[0:-4] + '_disclaim.mp3'
        insert_disclaimer(srcFile, disclaimFile)
        print("Result file : {}".format(disclaimFile))
