# -*- coding: utf-8 -*-
"""
schema cli

Usage:
  schema <username> <password>
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
import requests
import json
from operator import itemgetter
from datetime import datetime, date

def login(user, pwd):
  headers = {'User-Agent':'Mozilla/5.0 (X11; Linux x86_64; rv:108.0) Gecko/20100101 Firefox/108.0',
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
    'TE':'trailers'
  }

  s = requests.Session()
  r = s.get('https://goteborg.skola24.se', headers = headers)
  
  r = s.get('https://goteborg.skola24.se/Applications/Authentication/login.aspx?host=goteborg.skola24.se', headers = headers)

  r = s.get('https://service-sso1.novasoftware.se/saml-2.0/authenticate?customer=https%3a%2f%2fauth.goteborg.se%2fFIM%2fsps%2fskolfederation%2fsaml20&targetsystem=Skola24', headers = headers)

  postdata = {"SAMLRequest": r.text.split('name="SAMLRequest" value="')[1].split('"')[0]}
  r = s.post('https://auth.goteborg.se/FIM/sps/skolfederation/saml20/login', headers = headers, data = postdata)

  
  cookie_obj = requests.cookies.create_cookie(name="WASReqURL",value="http:///auth/Responder")
  s.cookies.set_cookie(cookie_obj)
  
  r2 = s.post('https://auth.goteborg.se/auth/j_security_check', data={'j_username':user,'j_password':pwd,'pw':'','login':'Logga in'}, headers = headers)

  if r2.text.__contains__('name="SAMLResponse" value="'):
    saml = r2.text.split('name="SAMLResponse" value="')[1].split('"')[0]
  else:
    raise Exception("Fel lösenord / användarnamn")

  headers["Origin"] = "https://auth.goteborg.se"
  headers["Referer"] = "https://auth.goteborg.se/"

  r = s.post('https://service-sso1.novasoftware.se/saml-2.0/response', data={"RelayState":"","SAMLResponse":saml}, headers = headers)

  return s

def json_serial(obj):
    """JSON serializer for objects not serializable by default json code"""

    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    raise TypeError ("Type %s not serializable" % type(obj))

def dateFromString(manad):
  manader = {
	"januari":1,
	"februari":2,
	"mars":3,
	"april":4,
        "maj":5,
        "juni":6,
        "juli":7,
        "augusti":8,
        "september":9,
        "oktober":10,
        "november":11,
        "december":12
  }
  try:
    return manader[manad]
  except:
    return 1

def getNarvaro(s,id):
  r5 = s.get("https://www.vklass.se/statistics/attendanceDetailed.aspx?userUID="+id)
  lista = []
  for data in r5.text.split("_manualCloseButtonText"):
    row = data.split('"text"')[1].split('}')[0]
    if row.__contains__("Status:"):
      rowdata = json.loads(row[1:])
      """Måndag 12 december 2022<br />kl: 10:45 - 11:40<br />Kurs: Matematik 1a <br />Status: Närvarande<br /><span style="color: red;">Sen ankomst:: 5 min</span>"""
      info = rowdata.split("<br />")
      date = info[0].split(" ")
      time = info[1].replace("kl: ","").split(" - ")
      hhmm = time[0].split(":")
      ehhmm = time[1].split(":")
      start = datetime(int(date[3]), dateFromString(date[2]), int(date[1]),int(hhmm[0]),int(hhmm[1]))
      end = datetime(int(date[3]), dateFromString(date[2]), int(date[1]),int(ehhmm[0]),int(ehhmm[1]))
      lektion = info[2].replace("Kurs: ","").strip()
      status = info[3].replace("Status: ","").strip()
      avvikelse = 0
      if len(info) == 5:
        avvikelse = int(info[4].split(">")[1].split("<")[0].split(":")[-1].strip().split(" ")[0])
      narvaro_entry = {
        "start":start,
        "end":end,
        "lektion":lektion,
        "status":status,
        "avvikelse": avvikelse
      }
      lista.append(narvaro_entry)
  return sorted(lista,key=itemgetter('start'))

def getKlass(s):
  r5 = s.get("https://www.vklass.se/Class.aspx")
  elever = []
  for data in r5.text.split("teacherStudentLink"):
    row = data.split('Info & resultat')[0]
    if row.__contains__('href="/User.aspx?id='):
      id_and_name = row.split("id=")[1].split('">')
      student = {
        "short_id":id_and_name[0],
        "name":id_and_name[1].split("</a>")[0],
        "uuid":row.split('/Results/StudentResult.aspx?id=')[1].split("&amp;")[0]
      }
      elever.append(student)
  return elever

if __name__ == "__main__":
  from docopt import docopt
  args = docopt(__doc__)
  print(login(args["<username>"],args["<password>"]))



