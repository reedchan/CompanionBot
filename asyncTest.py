import aiohttp
import asyncio
import async_timeout
import getopt
import io
import json
import re
import urllib.error
import urllib.request
from bs4 import BeautifulSoup
from os import path
from sys import argv, exit

from setup import getPokemon, getSoup

import time

user_agent = 'Mozilla/5.0 (Windows; U; Windows NT 10.0; rv:10.0) Gecko/20100101 Firefox/52.0'
sendHeader={'User-Agent':user_agent,}

# Dictionary for the national Pokédex
nationalDex = dict()

def help(returnCode):
  info = """\
Usage: %s [options...]
  -h, --help            Print this help message
""" % path.split(__file__)[1]
  print(info)
  exit(returnCode)
  
# Save writeDict by dumping it to a string in a JSON format and writing it to
# writeFile
# Print errorMsg if there is an exception
def saveDict(writeDict, writeFile, errorMsg):
  dictString = json.dumps(writeDict, sort_keys=True, indent=2)
  try:
    f = open(writeFile, "w")
    f.write(dictString)
    f.close()
  except Exception as e:
    if (errorMsg != ""):
      print(errorMsg)
    print(e)
    exit(1)
  return
  
def getDexURL():
  global nationalDex
  baseURL = "http://bulbapedia.bulbagarden.net"
  regions = {"Kanto", "Johto", "Hoenn", "Sinnoh", "Unova", "Kalos", "Alola"}
  soup = getSoup(targetURL="%s%s"%(baseURL, "/wiki/List_of_Pok%C3%A9mon_by_National_Pok%C3%A9dex_number"),
                 errorMsg="")
  tables = soup.find_all("table")
  for tableBody in tables:
    # not isdisjoint checks if any of the regions is in the table titles
    # can check tables[i].th.a["title"] for Kanto-Kalos, but not Alola
    # regions.isdisjoint(str(tables[1].th).split(" "))
    if ((tableBody is tables[7]) or
        (not regions.isdisjoint(str(tableBody.th).split(" ")))):
      rows = tableBody.find_all("tr")
      for row in rows:
        for link in row.find_all("a"):
          url = link.get("href")
          urlLower = url.lower()
          if (("Pok%C3%A9mon" in url) and (not "list" in urlLower)):
            url     = url.replace("%27", "'")
            urlRE   = re.compile("(/wiki/)|(_\(pok%c3%a9mon\))")
            pokemon = re.sub(urlRE, "", urlLower)
            # Farfetch'd
            if (pokemon.startswith("farfetch")):
              pokemon = pokemon.replace("%27", "'")
            elif (pokemon.startswith("nidoran")):
              # Nidoran F
              pokemon = pokemon.replace("%e2%99%80", "_(f)")
              # Nidoran M
              pokemon = pokemon.replace("%e2%99%82", "_(m)")
            # Flabébé
            elif (pokemon.startswith("flab")):
              pokemon = pokemon.replace("%c3%a9", "é")
            tempDict= dict()
            tempDict["url"] = baseURL + url
            nationalDex[pokemon] = tempDict
    # It's not a table that we're interested in
    else:
      continue
  return
  
async def getPokeInfo(mutex, key, session):
  tempDict = nationalDex[key]
  async with session.get(tempDict["url"]) as response:
    try:
      assert(response.status == 200)
      data = await response.read()
      soup = BeautifulSoup(data, "html.parser")
      tempDict.update(getPokemon(soup, key))
      # await mutex.acquire()
      nationalDex[key] = tempDict
      # print(tempDict)
      # mutex.release()
    except Exception as e:
      print(e)
  return

async def limitGetPokeInfo(sem, mutex, key, session):
  async with sem:
    await getPokeInfo(mutex, key, session)
  
async def getPokedex():
  # Semaphore to limit the maximum number of concurrent requests
  sem = asyncio.Semaphore(100)
  # Semaphore to ensure nationalDex correctness
  mutex = asyncio.Semaphore(1)
  tasks = []
  # Share a client session so it will not open a new session for each request
  async with aiohttp.ClientSession() as session:
    for key in nationalDex:
      task = asyncio.ensure_future(limitGetPokeInfo(sem, mutex, key, session))
      tasks.append(task)
      # url = nationalDex[key]["url"]
    await asyncio.gather(*tasks)
  # asd
  
def main(argv):
  start = time.time()
  shortOpts = "h"
  longOpts = ["help"]
  try:
    opts, args = getopt.getopt(argv[1:], shortOpts, longOpts)
  except Exception as e:
    print(e)
    help(2)
  for (o, a) in opts:
    if (o in ("-h", "--help")):
      help(2)
  getDexURL()
  loop = asyncio.get_event_loop()
  future = asyncio.ensure_future(getPokedex())
  loop.run_until_complete(future)
  loop.close()
  saveDict(writeDict=nationalDex,
           writeFile="pokedex.json",
           errorMsg="Error writing pokedex to pokedex.json")
  print("Took %d seconds" % (time.time() - start))
  return

if __name__ == '__main__':
  main(argv)