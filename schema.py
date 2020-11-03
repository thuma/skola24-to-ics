# -*- coding: utf-8 -*-
import requests
import arrow
import bottle
import json
from datetime import datetime
from os import listdir, system, mkdir
from bottle import route, run, response

hdata = {
  'Connection': 'keep-alive',
  'sec-ch-ua': '"Chromium";v="86", "\"Not\\A;Brand";v="99", "Google Chrome";v="86"',
  'Accept': 'application/json, text/javascript, */*; q=0.01',
  'X-Scope': '8a22163c-8662-4535-9050-bc5e1923df48',
  'X-Requested-With': 'XMLHttpRequest',
  'sec-ch-ua-mobile': '?0',
  'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/86.0.4240.111 Safari/537.36',
  'Content-Type': 'application/json',
  'Origin': 'https://web.skola24.se',
  'Sec-Fetch-Site': 'same-origin',
  'Sec-Fetch-Mode': 'cors',
  'Sec-Fetch-Dest': 'empty',
  'Referer': 'https://web.skola24.se/timetable/timetable-viewer/goteborg.skola24.se/Lindholmens%20tekniska%20gymnasium/',
  'Accept-Language': 'sv-SE,sv;q=0.9,en-US;q=0.8,en;q=0.7',
  'Cookie': 'ASP.NET_SessionId=lg4zfxaklbnb0qvh4nwctfmz'
}

def get_id_for(larare):
  return requests.post("https://web.skola24.se/api/encrypt/signature", headers=hdata, json={"signature": larare}).json()["data"]["signature"]

def get_key():
  return requests.post("https://web.skola24.se/api/get/timetable/render/key", headers=hdata, json="").json()["data"]["key"]


def get_week(week, larare):
    if week < 26:
        year = 2021
    else:
        year = 2020
 
    weekrequest = {
        'blackAndWhite': False,
        'customerKey': "",
        'endDate': None,
        'height': 850,
        'host': "goteborg.skola24.se",
        'periodText': "",
        'privateFreeTextMode': False,
        'privateSelectionMode': None,
        'renderKey': get_key(),
        'scheduleDay': 0,
        'selection': get_id_for(larare),
        'selectionType': 4,
        'showHeader': False,
        'startDate': None,
        'unitGuid': "ZmEyYzc4NWQtNzRjOC1mNzE3LTg5MGItOGVjZjExZTJmNGYw",
        'week': week,
        'width': 1400,
        'year': year
        }
    return json.loads(requests.post("https://web.skola24.se/api/render/timetable", headers=hdata, json=weekrequest ).json()["data"]["timetableJson"])

def tidtexter(textdata):
    return textdata["x"] > 50 and textdata["x"] < 1320 and textdata["y"] > 10

def get_weekdata(week_nr, larare):
    #71 -- 181 -- 293      323 --  433 -- 538      575 -- 685 -- 796       826 --  936 --  1041      1078 -- 1188 -- 1300
    indata = get_week(week_nr, larare)
    week = [[],[],[],[],[]]
    for text in indata["textList"]:
        if tidtexter(text):
            if text["x"] < 300:
                week[0].append(text)
            elif text["x"] < 550:
                week[1].append(text)
            elif text["x"] < 800:
                week[2].append(text)
            elif text["x"] < 1050:
                week[3].append(text)
            else:
                week[4].append(text)

    def ypos(text):
        return text['y']

    week[0].sort(key=ypos)
    week[1].sort(key=ypos)
    week[2].sort(key=ypos)
    week[3].sort(key=ypos)
    week[4].sort(key=ypos)
    return week

def todate(date, tid):
    tid = ("0"+tid)[-5:]
    return  arrow.get(arrow.get(date+"T"+tid+":00").datetime.replace(tzinfo=None), 'Europe/Stockholm').to("UTC").format('YYYYMMDDTHHmmss')+"Z"

def todatestr(week, day):
    if week < 26:
        year = "2021"
    else:
        year = "2020"
    return  arrow.get(arrow.get(year+"-W"+("0"+str(week))[-2:]+"-"+str(day)).datetime.replace(tzinfo=None), 'Europe/Stockholm').to("UTC").format('YYYY-MM-DD')


def geticsfor(larare):

    weeks = {}
    for week in range(1,53):
        weeks[week] = get_weekdata(week, larare)

    gra = [181, 433, 685, 936, 1188]

    events = []
    for week in weeks:
        for day in range(5):
            date = todatestr(week, day+2)
            gray = {"start":False, "end":False,"date":False}
            event = {"text":"", "date":date, "start":False}
            for line in weeks[week][day]:
                if len(line["text"]) > 3 and line["text"][-3] == ":" and gray["start"] and abs(gra[day] - line["x"]) < 40:
                    gray["end"] = line["text"]
                elif len(line["text"]) > 3 and line["text"][-3] == ":" and not gray["start"] and abs(gra[day] - line["x"]) < 40:
                    gray["start"] = line["text"]
                elif len(line["text"]) > 3 and line["text"][-3] == ":" and not event["start"]:
                    event["start"] = line["text"]
                elif len(line["text"]) > 3 and line["text"][-3] == ":" and event["start"]:
                    event["end"] = line["text"]
                    events.append(event)
                    event = { "text":"", "date":date, "start":False}
                elif "(" in line["text"]:
                    event["lokal"] = line["text"].split("(")[0].strip()
                else:
                    event["text"] += line["text"] + " "
            if gray["start"]:
                events.append({"start":gray["start"] ,"end":gray["end"], "date":date, "text":"Gråtid"})


    today = arrow.utcnow().format('YYYYMMDD')+"T000000Z"
    icsdata = "BEGIN:VCALENDAR"
    icsdata += "\r\nVERSION:2.0"
    icsdata += "\r\nPRODID:api.ltgee.seSCHEMA"
    for event in events:
        icsdata += "\r\nBEGIN:VEVENT"
        icsdata += "\r\nDTSTAMP:"+today
        icsdata += "\r\nUID:"+todate(event["date"], event["start"])+todate(event["date"], event["end"]) +event["text"].strip().split(" ")[0]
        icsdata += "\r\nSUMMARY:"+event["text"].strip().split(" ")[0]
        icsdata += "\r\nDTSTART:"+todate(event["date"], event["start"])
        icsdata += "\r\nDTEND:"+todate(event["date"], event["end"])
        if "lokal" in event:
            icsdata += "\r\nLOCATION:"+event["lokal"]
        icsdata += "\r\nDESCRIPTION:"+event["text"].strip()
        icsdata += "\r\nEND:VEVENT"
    icsdata += "\r\nEND:VCALENDAR"
    response.headers["Content-Disposition"] = 'attachment; filename="'+larare+'.ics"'
    response.content_type = 'text/calendar; charset=UTF8'
    return icsdata

@route('/schema/<larare>')
def schema(larare):
    return geticsfor(larare)

run(host='localhost', port=8080)
