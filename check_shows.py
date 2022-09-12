# this file checks the show archvie for the files listed in the input file
# specified with the -f argument. show length is 1 hour and it can be 
# overridden with the -l argument.
#
import os, datetime, getopt, sys
from datetime import datetime
from datetime import timedelta

ARCHIVE_DIR = "/Users/Barbara/tmp/kzsu-archive/"

list_file_name = None
show_hours = 2

def parse_args(argv):
   global list_file_name, show_hours

   try:
      opts, args = getopt.getopt(argv,"f:l:",["file","length"])
   except getopt.GetoptError:
      print ('find_missing.py -f <SHOW_LIST_FILE>')
      sys.exit(2)

   for opt, arg in opts:
      if opt == '-h':
         print ('find_missing.py -f <SHOW_LIST_FILE>')
         sys.exit()
      elif opt in ("-f", "--file"):
         list_file_name = arg;
      elif opt in ("-l", "--length"):
         show_hours = int(arg);

   #print ('Show args: -{}-.'.format(list_file_name))

if __name__ == '__main__':
    parse_args(sys.argv[1:])
    if list_file_name is None or not os.path.exists(list_file_name):
        print("Error: input file -{}- does not exist.".format(list_file_name))
        sys.exit(1)

    list_file = open(list_file_name)
    for line in list_file:
        if len(line) == 0:
            continue

        date = datetime.strptime(line, '%Y-%m-%d %H.%M\n')
        for hour in range(show_hours):
            filepath = datetime.strftime(date, '%Y/%b/%d/kzsu-%Y-%m-%d-%H00.mp3')
            havefile = os.path.exists(ARCHIVE_DIR + filepath)
            print("{}: {}".format(filepath, "Yes" if havefile else "No"))
            date = date + timedelta(hours=1)




    
