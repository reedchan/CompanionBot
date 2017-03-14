import getopt
import io
import json
import urllib.error
import urllib.request
from bs4 import BeautifulSoup
from os import path
from sys import argv, exit

# Import ElementTree as etree to parse the HTML tables for the prefixes
try:
  from defusedxml import ElementTree as etree
except ImportError:
  print("Please install defusedxml to safely parse the HTML tables.")
  from xml.etree import ElementTree as etree

user_agent = 'Mozilla/5.0 (Windows; U; Windows NT 10.0; rv:10.0) Gecko/20100101 Firefox/52.0'
sendHeader={'User-Agent':user_agent,}

# Dictionary for Terraria prefix IDs
prefixDict = dict()
# Dictionary for the national Pokédex
nationalDex = dict()

def help(returnCode):
  info = """\
Usage: %s [options...]
  -a, --all             Perform all setup operations
  -h, --help            Print this help message
  -p, --pokemon         Setup for Pokémon
  -t, --terraria        Setup for Terraria prefixes
""" % path.split(__file__)[1]
  print(info)
  exit(returnCode)

# Send a GET request to targetURL, read the data from the response, and return
# it as a BeautifulSoup object
# Print errorMsg if there is an exception raised by urllib or by BeautifulSoup
def getSoup(targetURL, errorMsg):
  try:
    req = urllib.request.Request(url=targetURL, data=None, headers=sendHeader)
    response = urllib.request.urlopen(req)
    data = response.read()
    soup = BeautifulSoup(data, "html.parser")
  except Exception as e:
    if (errorMsg != ""):
      print(errorMsg)
    print(e)
    exit(1)
  return soup

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

def main(argv):
  shortOpts = "ahpt"
  longOpts = ["all", "help", "pokemon", "terraria"]
  try:
    opts, args = getopt.getopt(argv[1:], shortOpts, longOpts)
  except Exception as e:
    print(e)
    help(2)
  # Whether or not to get the national Pokedex from Bulbapedia
  pokedex = False
  # Whether or not to get the prefixes from the official Terraria wiki
  prefixes = False
  for (o, a) in opts:
    if (o in ("-a", "--all")):
      pokedex = True
      prefixes = True
    elif (o in ("-h", "--help")):
      help(2)
    elif (o in ("-p", "--pokemon")):
      pokedex = True
    elif (o in ("-t", "--terraria")):
      prefixes = True
  if ((not pokedex) and (not prefixes)):
    print("Please specify what you would like to setup.")
    help(2)
  if (pokedex):
    baseURL = "http://bulbapedia.bulbagarden.net"
    regions = {"Kanto", "Johto", "Hoenn", "Sinnoh", "Unova", "Kalos", "Alola"}
    soup = getSoup(targetURL="%s%s"%(baseURL, "/wiki/List_of_Pok%C3%A9mon_by_National_Pok%C3%A9dex_number"),
                   errorMsg="")
    tables = soup.find_all("table")
    # tables[1] should be Kanto
    # tables[2] should be Johto
    # tables[3] should be Hoenn
    # tables[4] should be Sinnoh
    # tables[5] should be Unova
    # tables[6] should be Kalos
    # tables[7] should be Alola
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
            if (("Pok%C3%A9mon" in url) and (not "list" in url.lower())):
              pokemon = url.lower().replace("/wiki/", "").replace("_(pok%c3%a9mon)", "")
              nationalDex[pokemon] = baseURL + url
      # It's not a table that we're interested in
      else:
        continue
    saveDict(writeDict=nationalDex,
             writeFile="pokedex.json",
             errorMsg="Error writing pokedex to pokedex.json")
    pass
  if (prefixes):
    soup = getSoup(targetURL="http://terraria.gamepedia.com/Prefix_IDs",
                   errorMsg="")
    # Get the tables
    tables = soup.find_all("table")
    try:
      assert(len(tables) > 1)
      assert(tables[1]["class"] == ["terraria", "sortable"])
    except AssertionError:
      print("Page layout changed - script must be updated")
      exit(1)
    # Get the second table which should contain the prefix table
    # Next line works for xml.etree.ElementTree and for defusedxml.ElementTree
    table = etree.XML(str(tables[1]))
    for row in table:
      # Convert to lowercase and strip whitespace
      prefix  = row[0].text.lower().strip()
      id      = row[1].text.lower().strip()
      # Ignore the table headers
      if ((prefix == "prefix") or (id == "value")):
        continue
      else:
        if (prefix in prefixDict):
          prefixDict[prefix] = [prefixDict[prefix], id]
        else:
          prefixDict[prefix] = id
    saveDict(writeDict=prefixDict,
             writeFile="terrariaPrefixes.json",
             errorMsg="Error writing prefixes to terrariaPrefixes.json")
  return

if __name__ == '__main__':
  main(argv)