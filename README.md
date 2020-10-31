

0) Introduction

This file generates a RadioLogic DJ program file based upon the .mp3 files that are present
in the staging directory. This script is typicall invoked by the RadioLogik Scheduler program
that runs it as a pre-schedule script. It is typically run early in the morning before the first
scheduled show is due to air, eg 5:30am. The day's playlist is created by iterating over the .mp3
files for the given day, eg 2020_10_31_*.mp3. and createing a .rlprg file from them. After execution
RLDJ Scheduler loads the generated file, eg Monday.rlprg into RLDJ.

In order to prevent time skew due to incorrect show length, timed interrupts are used to control
program start and end times. If there is no program at the show end time then the Zootopia feed
is enabled by setting the LINE feed to true.

1) Program Updates
The system supports the ability to modify the playlist that is generated in the morning. This
is done clearing RLDJ's future events by click the "Clear List..." button (lower/right) and then manually
invoking the RLDJ Scheduler for the current weekday. This is done  as follows:

   * from Radilogik Scheduler Program Properties and Times view click the program day, eg Monday
   * click the 05:30 start time row in the Days/Start Time list (middle of screen)
   * click the Manually Build button (bottom of the Days/Start Time list element

When invoked in this manner the script will output only the programs that occur after the current
time. This is required because RLDJ attempts to play items that have occurred in the 'recent past'
in a misguided attempt to 'catch up' on past programs. Note that the scheduler should not be invoked
within 5 (ish) minutes of a program end since it can take several minutes for it to build and load
the revised program.

