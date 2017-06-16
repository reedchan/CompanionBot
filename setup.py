import getopt
import io
import json
import re
import traceback
import urllib.error
import urllib.request
from bs4 import BeautifulSoup
from os import path
from sys import argv, exc_info, exit

import time

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
  
def getExceptionDetails():
  _, _, tb = exc_info()
  traceback.print_tb(tb) # Fixed format
  tb_info = traceback.extract_tb(tb)
  filename, line, funct, text = tb_info[-1]
  return "An error occurred on line {} in statement {}.".format(line, text)
  
# Takes in soup, a BeautifulSoup object of a Pokemon's Bulbapedia page, and the
# Pokemon's name in order to return a formatted string with relevant info about
# the Pokemon
def getPokemon(soup, pokemon):
  # Dictionary with the Pokemon's info
  pokeDict = dict()
  infoTable = soup.find_all(name="table", style=re.compile("float:right*"))
  # Pokemon info
  embedImg  = ""      # Image of the Pokemon
  natDexNo  = ""      # National Pokédex number
  abilities = dict()  # Pokemon abilities
  pokeText  = ""      # Pokemon text e.g. "Seed Pokemon" for Bulbasaur
  # pokeTypes = []      # Pokemon types
  pokeTypes = dict()  # Pokemon types
  abilities = dict()  # Pokemon abilities
  baseStats = dict()  # Pokemon base stats
  prettyPoke = " ".join(p.capitalize() for p in pokemon.split("_"))
  try:
    assert(len(infoTable) == 1)
  except:
    print("Page layout changed - Need to update the bot")
  infoTable = infoTable[0]
  # Be careful with the following pokemon
  # sawsbuck  (image)
  # farfetchd (apostrophe in the name)
  # type: null (space in the name)
  # tapu koko (space in the name)
  # meloetta
  # nidoran (special char in the name)
  # charizard (multiple megas)
  # zigzagoon (something about the pokemon category)
  # azumarill (something about the pokemon category)
  try:
    embedImg = infoTable.find(name="a", attrs={"class": "image"})
    embedImg = embedImg.find(name="img")
    embedImg = embedImg.get("src")
    pokeDict["img"] = embedImg
  except Exception as e:
    print(e)
    print("Error getting embedImg for %s" % prettyPoke)
    exit(1)
  try:
    pokeText = infoTable.find(name="a", title=re.compile("Pok.mon category"))
    # Have the Pokemon category
    if (not pokeText.string is None):
      pokeText = pokeText.string
    # Pokemon category has an explanation on Bulbapedia
    # i.e. if you hover over it
    else:
      pokeText = pokeText.find(name="span", attrs={"class": "explain"})
      pokeText = pokeText.string
    if (not " Pok\u00e9mon" in pokeText):
      pokeText = pokeText + " Pok\u00e9mon"
    # Cannot write 'é' to a file"
    pokeDict["category"] = pokeText
  except Exception as e:
    print(e)
    print("Error getting pokeText for %s" % prettyPoke)
    exit(1)
  try:
    dexRE = re.compile("List of Pokémon by National Pokédex number")
    natDexNo = infoTable.find(name="a", title=dexRE)
    natDexNo = natDexNo.string
    pokeDict["natDexNo"] = natDexNo
  except Exception as e:
    print(e)
    print("Error getting National Pokedex number for %s" % prettyPoke)
    exit(1)
  try:
    typeRE = re.compile("(?<!Unknown )\(type\)")
    types = infoTable.find_all(name="a", title=typeRE)
    typeSet = []
    tempTypes = []
    for type in types:
      tempTable = type.find_parent("table")
      add = True
      for setTable in typeSet:
        if (tempTable is setTable):
          add = False
      if (add):
        typeSet += [tempTable]
    # Mega evolutions that may be a different type
    if (len(typeSet) > 1):
      while(len(typeSet) > 0):
        typeTable = typeSet.pop()
        # tempTypes = [typeTable.find_parent("td").find("small").string]
        key = typeTable.find_parent("td").find("small").string
        for type in typeTable.find_all(name="a", title=typeRE):
          if (key in pokeTypes):
            pokeTypes[key] = pokeTypes[key] + ";" + type.string
          else:
            pokeTypes[key] = type.string
          # tempTypes += [type.string]
        # pokeTypes += [tempTypes]
    # No mega evolutions
    else:
      # tempTypes += [prettyPoke]
      key = prettyPoke
      for type in types:
        if (key in pokeTypes):
          pokeTypes[key] = pokeTypes[key] + ";" + type.string
        else:
          pokeTypes[key] = type.string
        # tempTypes += [type.string]
      # pokeTypes += [tempTypes]
      # pokeTypes += [tempTypes]
    pokeDict["types"] = pokeTypes
  except Exception as e:
    print(e)
    print("Error getting types for %s" % prettyPoke)
    exit(1)
  # abilities
  try:
    # Find the link in the table for abilities
    abilityLink = infoTable.find(name="a", title="Ability")
    assert(abilityLink != None)
    # Find the parent table
    abilitiesTable = abilityLink.find_parent(name="td")
    # Find all of the table cells that will have the abilities
    abilitiesCells = abilitiesTable.find_all(name="td")
    for ability in abilitiesCells:
      # Filter out abilities that aren't displayed
      # e.g. unused "Cacophony" ability
      if (("style" in ability.attrs) and
          ("display: none" in ability.attrs["style"])):
        continue
      else:
        try:
          # Subtitles (e.g. "Hidden Ability", "Mega Charizard X", etc.)
          key = ability.small.string.strip()
        # No subtitle which implies that it's a normal ability so leave it blank
        except:
          key = prettyPoke
        if (key in abilities):
          abilities[key] = abilities[key] + ";" + ability.a.string
        else:
          abilities[key] = ability.a.string
    pokeDict["abilities"] = abilities
  except Exception as e:
    print(e)
    print("Error getting hidden abilities for %s" % prettyPoke)
    exit(1)
  # base stats
  try:
    statTables = soup.find_all(name="table", align="left")
    for table in statTables:
      if (table.span.string != "Stat"):
        continue
      title = table.find_previous().string
      if (title == "Base stats"):
        title = prettyPoke
      tempDict = dict()
      # Get the tag with the numbers for a stat
      baseStat  = table.find_next(name="td")
      # Get the tag with the stat range at level 50
      range50   = baseStat.find_next(name="small")
      # Get the stat range at level 100
      range100  = range50.find_next(name="small").string
      # Get the base stat from the cell
      # baseStat  = baseStat.find_next(name="th").find_next(name="th").string.strip()
      # Get the stat range at level 50
      range50   = range50.string
      tempDict[baseStat.a.string] = """\
%s;%s;%s""" % (baseStat.find_next(name="th").find_next(name="th").string.strip(),
               range50, range100)
      # Do this 5 more times (total of 6) to get all the stats
      for i in range(0, 5):
        baseStat  = baseStat.find_next(name="td").find_next(name="td")
        range50   = baseStat.find_next(name="small")
        range100  = range50.find_next(name="small").string
        range50   = range50.string
        tempDict[baseStat.a.string] = """\
%s;%s;%s""" % (baseStat.find_next(name="th").find_next(name="th").string.strip(),
               range50, range100)
      baseStat  = baseStat.find_next(name="td").find_next(name="td")
      tempDict["Total"] = baseStat.find_next("th").find_next("th").string.strip()
      baseStats[title] = tempDict
    pokeDict["baseStats"] = baseStats
  except Exception as e:
    print(e)
    errorMsg = getExceptionDetails()
    print(errorMsg)
    print("Error getting base stats for %s" % prettyPoke)
    exit(1)
  # use find_previous to find what pokemon the stat is for
  return pokeDict
  
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
  start = time.time()
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
    print("Preparing Pokédex (this may take a while)...")
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
    for key in nationalDex:
      tempDict = nationalDex[key]
      soup = getSoup(targetURL=tempDict["url"],
                     errorMsg="")
      tempDict.update(getPokemon(soup, key))
      nationalDex[key] = tempDict
  if (prefixes):
    print("Preparing Terraria prefixes...")
    soup = getSoup(targetURL="http://terraria.gamepedia.com/Prefix_IDs",
                   errorMsg="")
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
  if (pokedex):
    print("Writing pokedex to pokedex.json...")
    saveDict(writeDict=nationalDex,
             writeFile="pokedex.json",
             errorMsg="Error writing pokedex to pokedex.json")
    print("Done!")
  if (prefixes):
    print("Writing prefixes to terrariaPrefixes.json...")
    saveDict(writeDict=prefixDict,
             writeFile="terrariaPrefixes.json",
             errorMsg="Error writing prefixes to terrariaPrefixes.json")
    print("Done!")
  print("Took %d seconds" % (time.time() - start))
  return

if __name__ == '__main__':
  main(argv)