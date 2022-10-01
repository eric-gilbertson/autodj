#!/usr/bin/python
#
# removes a chunk from an audio file between startTime and endTime and writes
# it to <INPUT_FILE>.clean
#
import os, subprocess, sys, datetime

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

def remove_chunk(srcFile, startTime, endTime):
    tmp1 = '/tmp/segment_extract1.mp3'
    tmp2 = '/tmp/segment_extract2.mp3'
    outFile = srcFile[0:-4] + ".clean.mp3"

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



if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: remove_chunk <START_TIME> <END_TIME>  <FILE_NAME>")
    else:
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

