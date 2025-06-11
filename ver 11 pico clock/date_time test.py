from datetime import datetime

now = datetime.now()

string = datetime.isoformat(now)

date = string.split('T')

time = date[1]
date = date[0]

year = date.split('-')
date = year[2]
month = year[1]
year = year[0]

sec = time.split(':')
hour = sec[0]
minute = sec[1]
sec = sec[2][:2]

weekday = datetime.weekday(now)

p = f"CLOCK|{hour}|{minute}|{sec}|{date}|{month}|{year}|{weekday}"
print(p.split('|'))