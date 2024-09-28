# Python program to illustrate Python get current time
# Importing datetime module
from datetime import datetime
 
# storing the current time in the variable
c = datetime.now()

# Displays Time
current_time = c.strftime('%d%m%Y%H%M%S')
print('Current Time is:', current_time)