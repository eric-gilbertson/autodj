from datetime import datetime
import random

class SpecialEvent(object):
    def __init__(self, date):
        self.date = date
        self.hours = []

    def addEvent(self, start, end):
        self.hours.append((start, end))

class ShowInfo(object):
    def __init__(self, date, start, duration, id, title):
        self.date = date,
        self.start = start
        self.duration = duration
        self.id = id
        self.title = title

class ShowDayInfo(object):
    def __init__(self, date, shows):
       self.date = date
       self.shows = shows

shows = []
date = datetime.strptime('2022-08-01', '%Y-%m-%d')
for day in range(100):
    start_hour = 8.0
    for show in range(4):
        duration = random.randrange(0,4)
        shows.append(ShowInfo(date, 12.0, 2.0, 33, 'Mr. Goodbar'))

#date = datetime.strptime('2022-08-02', '%Y-%m-%d')
#s1 = ShowInfo(date, 7.0, 2.0, 33, 'Day2_Show1')
#s2 = ShowInfo(date, 13.0, 1.0, 33, 'Day2_Show2')
#s3 = ShowInfo(date, 20.0, 2.0, 33, 'Day2_Show3')
#days.append(ShowDayInfo(datetime.strptime('2022-08-02', '%Y-%m-%d'), [s1, s2, s3]))

#s1 = ShowInfo(2.0, 2.0, 33, 'Day3_Show1')
#s2 = ShowInfo(3.0, 1.0, 33, 'Day3_Show2')
#s3 = ShowInfo(18.0, 2.0, 33, 'Day3_Show3')
#days.append(ShowDayInfo(datetime.strptime('2022-08-02', '%Y-%m-%d'), [s1, s2, s3]))

se1 = SpecialEvent(datetime.strptime('2022-08-01', '%Y-%m-%d'))
se1.addEvent(9.0, 11.0)
print("events: {}".format(len(se1.hours)))

#print("shows : {}".format(len(days)))

#fill_slot(duration)
    

    




