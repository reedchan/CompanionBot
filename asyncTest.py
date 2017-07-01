import aiohttp
import asyncio
import async_timeout
import getopt
import json
import logging
import re
from bs4 import BeautifulSoup
from os import path
from sys import argv, exit

from setup import getPokemon, getSoup

user_agent = 'Mozilla/5.0 (Windows; U; Windows NT 10.0; rv:10.0) Gecko/20100101 Firefox/52.0'
sendHeader={'User-Agent':user_agent,}

# Dictionary for the national Pokédex
nationalDex = dict()
# Dictionary for the Terraria prefixes
prefixDict  = dict()

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
      logging.error(errorMsg)
    logging.error(e)
    exit(1)
  return
  
async def getDexURL(session):
  global nationalDex
  baseURL = "http://bulbapedia.bulbagarden.net"
  async with session.get("%s%s"%(baseURL, "/wiki/List_of_Pok%C3%A9mon_by_National_Pok%C3%A9dex_number")) as response:
    try:
      assert(response.status == 200)
      data = await response.read()
      soup = BeautifulSoup(data, "html.parser")
    except Exception as e:
      logging.error(e)
  regions = {"Kanto", "Johto", "Hoenn", "Sinnoh", "Unova", "Kalos", "Alola"}
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
  
async def getPrefixes(session):
  global prefixDict
  async with session.get("http://terraria.gamepedia.com/Prefix_IDs") as response:
    try:
      assert(response.status == 200)
      data = await response.read()
      soup = BeautifulSoup(data, "html.parser")
    except Exception as e:
      logging.error(e)
  # Get the tables
  tables = soup.find_all("table")
  for tableBody in tables:
    # Select the correct table
    if (tableBody.attrs == {'class': ['terraria', 'sortable']}):
      rows = tableBody.find_all("tr")
      for row in rows:
        cols = row.find_all("td")
        if (len(cols) == 2):
          prefix  = cols[0].string.lower().strip()
          id      = cols[1].string.lower().strip()
          # Prefix that has multiple IDs
          if (prefix in prefixDict):
            prefixDict[prefix] = [prefixDict[prefix], id]
          else:
            prefixDict[prefix] = id
        # Ignore the table headers
        else:
          assert(len(row.find_all("th")) != 0)
          continue
    else:
      continue
  return
  
async def getPokeInfo(key, session):
  tempDict = nationalDex[key]
  async with session.get(tempDict["url"]) as response:
    try:
      assert(response.status == 200)
      data = await response.read()
      soup = BeautifulSoup(data, "html.parser")
    except Exception as e:
      logging.error(e)
  tempDict.update(getPokemon(soup, key))
  nationalDex[key] = tempDict
  return

async def limitGetPokeInfo(sem, key, session):
  async with sem:
    await getPokeInfo(key, session)
  
async def getPokedex():
  # Semaphore to limit the maximum number of concurrent requests
  sem = asyncio.Semaphore(128)
  tasks = []
  # Share a client session so it will not open a new session for each request
  async with aiohttp.ClientSession() as session:
    for key in nationalDex:
      task = asyncio.ensure_future(limitGetPokeInfo(sem, key, session))
      tasks.append(task)
    await asyncio.wait(tasks)
  return
  
async def setup():
  # Semaphore to limit the maximum number of concurrent requests
  sem = asyncio.Semaphore(128)
  tasks = []
  # Share a client session so it will not open a new session for each request
  async with aiohttp.ClientSession() as session:
    tasks.append(asyncio.ensure_future(getDexURL(session)))
    tasks.append(asyncio.ensure_future(getPrefixes(session)))
    await asyncio.wait(tasks)
  return
  
def main(argv):
  logFormat   = "%(asctime)s %(levelname)s %(message)s"
  dateFormat  = "%Y-%m-%d %H:%M:%S UTC-%z"
  logging.basicConfig(format=logFormat, datefmt=dateFormat, level=10)
  shortOpts = "h"
  longOpts = ["help"]
  try:
    opts, args = getopt.getopt(argv[1:], shortOpts, longOpts)
  except getopt.GetoptError as e:
    logging.error(e)
    help(2)
  for (o, a) in opts:
    if (o in ("-h", "--help")):
      help(2)
  # It's the same event loop so don't close it until the end
  # No need to call asyncio.new_event_loop since we have run_until_complete()
  loop = asyncio.get_event_loop()
  # Finish setup before completing the pokedex
  loop.run_until_complete(asyncio.ensure_future(setup()))
  loop.run_until_complete(asyncio.ensure_future(getPokedex()))
  loop.close()
  saveDict(writeDict=nationalDex,
           writeFile="pokedex.json",
           errorMsg="Error writing pokedex to pokedex.json")
  saveDict(writeDict=prefixDict,
           writeFile="terrariaPrefixes.json",
           errorMsg="Error writing prefixes to terrariaPrefixes.json")
  return

if __name__ == '__main__':
  main(argv)