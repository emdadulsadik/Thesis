import time
from initial_scheduler import schedule

########################################################
# initial schedule: assign machines to processors.
########################################################

while True:
    schedule()
    time.sleep(600)

########################################################
