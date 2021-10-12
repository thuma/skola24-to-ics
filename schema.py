# -*- coding: utf-8 -*-
import requests
import arrow
import bottle
import json
from datetime import datetime
from os import listdir, system, mkdir
from bottle import route, run, response, post, get, request
from time import time
import sqlite3
conn = sqlite3.connect('attendance.db')

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
        year = 2022
    else:
        year = 2021

    weekrequest = {
        'blackAndWhite': False,
        'customerKey': "",
        'endDate': None,
        'height': 550,
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
        'width': 1200,
        'year': year
        }
    data = requests.post("https://web.skola24.se/api/render/timetable", headers=hdata, json=weekrequest ).json()
    return data["data"]["lessonInfo"]

def tidtexter(textdata):
    return textdata["x"] > 50 and textdata["x"] < 1320 and textdata["y"] > 10

def get_weekdata(week_nr, larare):
    indata = get_week(week_nr, larare)
    week = [[],[],[],[],[]]
    if indata:
        for event in indata:
            week[event["dayOfWeekNumber"] - 1].append(event)
    return week

def todate(date, tid):
    return  arrow.get(arrow.get(date+"T"+tid).datetime.replace(tzinfo=None), 'Europe/Stockholm').to("UTC").format('YYYYMMDDTHHmmss')+"Z"

def todatestr(week, day):
    if week < 26:
        year = "2022"
    else:
        year = "2021"
    return  arrow.get(arrow.get(year+"-W"+("0"+str(week))[-2:]+"-"+str(day)).datetime.replace(tzinfo=None), 'Europe/Stockholm').to("UTC").format('YYYY-MM-DD')


def geticsfor(larare):

    weeks = {}
    for week in range(1,53):
        weeks[week] = get_weekdata(week, larare)

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
                    event["lokal"] = line["texts"][2]
                    event["summary"] = line["texts"][0]
                else:
                    event["text"] = "Gråtid"
                    event["summary"] = "Gråtid"
                events.append(event)

    today = arrow.utcnow().format('YYYYMMDD')+"T000000Z"
    icsdata = "BEGIN:VCALENDAR"
    icsdata += "\r\nVERSION:2.0"
    icsdata += "\r\nPRODID:api.ltgee.seSCHEMA"
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
    response.headers["Content-Disposition"] = 'attachment; filename="'+larare+'.ics"'
    response.content_type = 'text/calendar; charset=UTF8'
    return icsdata

def addsal(sal, atid):
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS attended
             (time int, atid text, sal text)''')
    c.execute("INSERT INTO attended VALUES (?,?,?)", (time(), atid, sal))
    conn.commit()

def getsal(sal):
    c = conn.cursor()
    for row in c.execute('SELECT time, atid FROM attended WHERE sal = ?',(sal,)):
        yield {"time":int(row[0])*1000,"atid":row[1]}

@route('/schema/<larare>')
def schema(larare):
    return geticsfor(larare)

@post('/attendance/<sal>')
def addsal_s(sal):
    atid = request.forms.get('atid')
    return addsal(sal, atid)

@get('/attendance/<sal>')
def getsal_s(sal):
    return json.dumps({"attended":list(getsal(sal))})

run(host='localhost', port=8080)
