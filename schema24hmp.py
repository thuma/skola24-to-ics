"""Schema 24

Usage:
  schema24.py <id>

"""

"""
Shola24 to ICS accessing skola24 data and export it to ics.
Copyright (C) 2023  Martin Harari Thuresson

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <https://www.gnu.org/licenses/>.
"""
from gevent import monkey
monkey.patch_all()
import os
import sys
sys.path.insert(0, os.path.dirname(__file__))
import requests
import arrow
import json
from datetime import datetime
from time import time
import urllib.parse
from docopt import docopt

hdata = {'User-Agent':'Mozilla/5.0 (X11; Linux x86_64; rv:108.0) Gecko/20100101 Firefox/108.0',
    'Accept':'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
    'Accept-Language':'sv-SE,sv;q=0.8,en-US;q=0.5,en;q=0.3',
    'Accept-Encoding':'gzip, deflate, br',
    'Cache-Control': 'no-cache',
    'Pragma': 'no-cache',
    'Connection':'keep-alive',
    'Upgrade-Insecure-Requests':'1',
    'Sec-Fetch-Dest':'document',
    'Sec-Fetch-Mode':'navigate',
    'Sec-Fetch-Site':'none',
    'Sec-Fetch-User':'1',
    'Origin' : "https://web.skola24.se", 
    'Referer' : "https://web.skola24.se/timetable/timetable-viewer/helsingborg.skola24.se/Maria%20Parkskolan/",
    "X-Requested-With": "XMLHttpRequest",
    "X-Scope": "8a22163c-8662-4535-9050-bc5e1923df48"
  }

def get_id_for(larare, s):
  singsresp = s.post("https://web.skola24.se/api/encrypt/signature", headers=hdata, json={"signature": larare})
  return singsresp.json()["data"]["signature"]

def get_key(s):
  keyr = s.post("https://web.skola24.se/api/get/timetable/render/key", headers=hdata, json="")
  return keyr.json()["data"]["key"]

def get_week(week, larare_id, s):
    if week == 26:
      return None

    if arrow.now().week < 26:
      htyear = arrow.now().year-1
      vtyear = arrow.now().year
    else:
      htyear = arrow.now().year
      vtyear = arrow.now().year+1

    if week < 26:
      year = vtyear
    else:
      year = htyear

    weekrequest = {
        'blackAndWhite': False,
        'customerKey': "",
        'endDate': None,
        'height': 550,
        'host': "helsingborg.skola24.se",
        'periodText': "",
        'privateFreeTextMode': False,
        'privateSelectionMode': None,
        'renderKey': get_key(s),
        'scheduleDay': 0,
        'schoolYear':'3f62ff4b-2f41-4ae9-900b-7bcd1254dcb5',
        'selection': larare_id,
        'selectionType': 4,
        'showHeader': False,
        'startDate': None,
        'unitGuid': "ZmIxMjhmNWUtYzQzMS1mMzg1LTllYjItNWUxMzBkOTQyYmE4",
        'week': week,
        'width': 1200,
        'year': year
        }  
    data = s.post("https://web.skola24.se/api/render/timetable", headers=hdata, json=weekrequest ).json()
    return data["data"]["lessonInfo"]

def tidtexter(textdata):
    return textdata["x"] > 50 and textdata["x"] < 1320 and textdata["y"] > 10

def get_weekdata(week_nr, larare_id, s):
    indata = get_week(week_nr, larare_id, s)
    week = [[],[],[],[],[]]
    if indata:
        for event in indata:
            week[event["dayOfWeekNumber"] - 1].append(event)
    return week

def todate(date, tid):
    return arrow.get(arrow.get(date+"T"+tid).datetime.replace(tzinfo=None), 'Europe/Stockholm').to("UTC").format('YYYYMMDDTHHmmss')+"Z"

def todatestr(week, day):
    if arrow.now().week < 26:
      htyear = arrow.now().year-1
      vtyear = arrow.now().year
    else:
      htyear = arrow.now().year
      vtyear = arrow.now().year+1

    if week < 26:
      year = str(vtyear)
    else:
      year = str(htyear)

    return arrow.get(arrow.get(year+"-W"+("0"+str(week))[-2:]+"-"+str(day)).datetime.replace(tzinfo=None), 'Europe/Stockholm').to("UTC").format('YYYY-MM-DD')

def geticsfor(larare):
    s = requests.session()

    weeks = {}
    larare_id = get_id_for(larare, s)
    for week in range(1,53):
        weeks[week] = get_weekdata(week, larare_id, s)

    events = []
    for week in weeks:
        for day in range(5):
            date = todatestr(week, day+2)
            for line in weeks[week][day]:
                event = {"date":date}
                event["end"] = line["timeEnd"]
                event["uid"] = line["guidId"]
                event["start"] = line["timeStart"]
                event["summary"] = ""
                if line["texts"]:
                    event["text"] = " ".join(line["texts"])
                    try:
                      event["lokal"] = line["texts"][2]
                    except:
                      event["lokal"] = ""
                    event["summary"] = line["texts"][0]
                else:
                    event["text"] = "Gråtid"
                    event["summary"] = "Gråtid"
                events.append(event)

    today = arrow.utcnow().format('YYYYMMDD')+"T000000Z"
    icsdata = "BEGIN:VCALENDAR"
    icsdata += "\r\nVERSION:2.0"
    icsdata += "\r\nPRODID:molndal.skola24.seSCHEMA"
    icsdata += "\r\nX-WR-CALNAME:Schema "+larare
    for event in events:
        icsdata += "\r\nBEGIN:VEVENT"
        icsdata += "\r\nDTSTAMP:"+today
        icsdata += "\r\nUID:"+event["uid"]+event["date"].replace("-","")
        icsdata += "\r\nSUMMARY:"+event["summary"]
        icsdata += "\r\nDTSTART:"+todate(event["date"], event["start"])
        icsdata += "\r\nDTEND:"+todate(event["date"], event["end"])
        if "lokal" in event:
            icsdata += "\r\nLOCATION:"+event["lokal"]
        icsdata += "\r\nDESCRIPTION:"+event["text"].strip()
        if event["text"] == "Gråtid":
            icsdata += "\r\nTRANSP:TRANSPARENT"
        icsdata += "\r\nEND:VEVENT"
    icsdata += "\r\nEND:VCALENDAR"
    return icsdata.encode("utf-8")

def application(environ, start_response):
    larare = environ["PATH_INFO"].split("/")[1]
    larare = urllib.parse.unquote(larare)
    data = geticsfor(larare)
    start_response('200 OK', [('Content-Type', 'text/calendar; charset=UTF8'),("Content-Disposition",'attachment; filename="'+larare+'.ics"')])
    return [data]

if __name__ == '__main__':
    arguments = docopt(__doc__, version='Schema 24')
    icsdata = geticsfor(arguments["<id>"])
    print(icsdata) 