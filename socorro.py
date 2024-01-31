import datetime

now = datetime.date.today()

# convert to string
date_time_str = now.strftime("%d/%m/%Y")
print('DateTime String:', date_time_str)