# Standard Python modules
import logging
import os
import re
import sys
# Non-standard Python modules
import aiohttp
import discord
from bs4 import BeautifulSoup
from discord.ext import commands

user_agent = 'Mozilla/5.0 (Windows; U; Windows NT 10.0; rv:10.0) Gecko/20100101 Firefox/52.0'
sendHeader={'User-Agent':user_agent,}

class Pokemon:
  """Pokemon-related commands."""
  def  __init__(self, bot):
    self.bot = bot
    self.pokedex = None
  
  # Takes in soup, a BeautifulSoup object of a Pokemon's Bulbapedia page, and the
  # Pokemon's name in order to return a formatted string with relevant info about
  # the Pokemon
  def getPokeData(self, soup, pokemon):
    """Create a dictionary containing the data for a Pokemon based on a
    BeautifulSoup object of its Bulbapedia page."""
    # Dictionary with the Pokemon's info
    pokeDict = dict()
    infoTable = soup.find_all(name="table", style=re.compile("float:right*"))
    # Pokemon info
    embedImg    = ""      # Image of the Pokemon
    natDexNo    = ""      # National Pokédex number
    abilities   = dict()  # Pokemon abilities
    pokeText    = ""      # Pokemon text e.g. "Seed Pokemon" for Bulbasaur
    pokeTypes   = dict()  # Pokemon types
    abilities   = dict()  # Pokemon abilities
    baseStats   = dict()  # Pokemon base stats
    prettyPoke  = " ".join(map(lambda x: x.capitalize(), pokemon.split("_")))
    try:
      assert(len(infoTable) == 1)
    except:
      logging.error("Page layout changed - Need to update the bot")
      return False
    infoTable = infoTable[0]
    try:
      embedImg = infoTable.find(name="a", attrs={"class": "image"})
      embedImg = embedImg.find(name="img")
      embedImg = embedImg.get("src")
      pokeDict["img"] = embedImg
    except Exception as e:
      logging.error(e)
      logging.error("Error getting embedImg for %s" % prettyPoke)
      return False
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
      logging.error(e)
      logging.error("Error getting pokeText for %s" % prettyPoke)
      return False
    try:
      dexRE = re.compile("List of Pokémon by National Pokédex number")
      natDexNo = infoTable.find(name="a", title=dexRE)
      natDexNo = natDexNo.string
      pokeDict["natDexNo"] = natDexNo
    except Exception as e:
      logging.error(e)
      logging.error("Error getting National Pokedex number for %s" % prettyPoke)
      return False
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
          key = typeTable.find_parent("td").find("small").string
          for type in typeTable.find_all(name="a", title=typeRE):
            if (key in pokeTypes):
              pokeTypes[key] = pokeTypes[key] + ";" + type.string
            else:
              pokeTypes[key] = type.string
      # No mega evolutions
      else:
        key = prettyPoke
        for type in types:
          if (key in pokeTypes):
            pokeTypes[key] = pokeTypes[key] + ";" + type.string
          else:
            pokeTypes[key] = type.string
      pokeDict["types"] = pokeTypes
    except Exception as e:
      logging.error(e)
      logging.error("Error getting types for %s" % prettyPoke)
      return False
    # Abilities
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
      logging.error(e)
      logging.error("Error getting hidden abilities for %s" % prettyPoke)
      return False
    # Base stats
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
        # Get the stat range at level 50
        range50   = range50.string
        nextNextTh = lambda x: x.find_next(name="th").find_next(name="th").string.strip()
        tempDict[baseStat.a.string] = """\
{};{};{}""".format(nextNextTh(baseStat), range50, range100)
        # Do this 5 more times (total of 6) to get all of the stats
        for i in range(0, 5):
          baseStat  = baseStat.find_next(name="td").find_next(name="td")
          range50   = baseStat.find_next(name="small")
          range100  = range50.find_next(name="small").string
          range50   = range50.string
          tempDict[baseStat.a.string] = """\
{};{};{}""".format(nextNextTh(baseStat), range50, range100)
        baseStat  = baseStat.find_next(name="td").find_next(name="td")
        tempDict["Total"] = nextNextTh(baseStat)
        baseStats[title] = tempDict
      pokeDict["baseStats"] = baseStats
    except Exception as e:
      logging.error(e)
      errorMsg = getExceptionDetails()
      logging.error(errorMsg)
      logging.error("Error getting base stats for %s" % prettyPoke)
      return False
    # use find_previous to find what pokemon the stat is for
    return pokeDict
    
  def getPokeEmbed(self, pokeDict, species):
    """Create a formatted Discord Embed object for a Pokemon based on a
    dictionary containing its data."""
    pokeName    = list(map(lambda x:x.capitalize(), species.split("_")))
    pokeName    = " ".join(pokeName)
    prettyName  = pokeName.replace("(m)", "\u2642").replace("(f)", "\u2640")
    pokeEmbed = discord.Embed(title=prettyName,
                              description="{}: {}".format(pokeDict["natDexNo"],
                                                          pokeDict["category"]),
                              url=self.pokedex[species])
    types     = pokeDict["types"]
    abilities = pokeDict["abilities"]
    baseStats = pokeDict["baseStats"]
    if (len(types) == 1):
      pokeEmbed.add_field(name="Types",
                          value=list(types.values())[0].replace(";", ", "),
                          inline=False)
    else:
      typeStr = []
      for type in sorted(types.items()):
        typeStr.append("{}: {}".format(type[0], type[1].replace(";", ", ")))
      pokeEmbed.add_field(name="Types", value="\n".join(typeStr), inline=False)
    if (len(abilities) == 1):
      pokeEmbed.add_field(name="Abilities",
                          value=list(abilities.values())[0].replace(";", ", "),
                          inline=False)
    else:
      abilityStr = []
      for ability in sorted(abilities.items()):
        abilityStr.append("{}: {}".format(ability[0].replace("(m)", "\u2642").replace("(f)", "\u2640"),
                                          ability[1].replace(";", ", ")))
      pokeEmbed.add_field(name="Abilities", value="\n".join(abilityStr), inline=False)
    statStr = []
    statStr.append("```{:^15}{:^24}".format("Stat", "Range"))
    statStr.append("{:15}{:^12}{:^12}".format("", "At Lv. 50", "At Lv. 100"))
    getValues   = lambda key,stat: baseStats[key][stat].split(";")
    appendStat  = lambda key, stat: statStr.append("{0:<9}{1[0]:<6}{1[1]:^12}{1[2]:^12}".format("{}:".format(stat), getValues(key, stat)))
    keys = sorted(baseStats.keys())
    # Experienced errors with Deoxys probably because of the many forms
    # Limit the base stats to reduce the character count
    # Probably hitting the character limit
    # TODO: remove limit if the character limit is upped or removed
    if (len(keys) > 3):
      count = 0
      for key in keys:
        if (count == 3):
          break
        statStr.append("{}".format(key.replace("(m)", "\u2642").replace("(f)", "\u2640")))
        appendStat(key, "HP")
        appendStat(key, "Attack")
        appendStat(key, "Defense")
        appendStat(key, "Sp.Atk")
        appendStat(key, "Sp.Def")
        appendStat(key, "Speed")
        statStr.append("{0:<9}{1[0]}".format("{}:".format("Total"), getValues(key, "Total")))
        count += 1
      statStr.append("Check Bulbapedia for more stats.")
    else:
      for key in keys:
        statStr.append("{}".format(key.replace("(m)", "\u2642").replace("(f)", "\u2640")))
        appendStat(key, "HP")
        appendStat(key, "Attack")
        appendStat(key, "Defense")
        appendStat(key, "Sp.Atk")
        appendStat(key, "Sp.Def")
        appendStat(key, "Speed")
        statStr.append("{0:<9}{1[0]}".format("{}:".format("Total"), getValues(key, "Total")))
    statStr.append("```")
    pokeEmbed.add_field(name="Base Stats", value="\n".join(statStr), inline=False)
    pokeEmbed.set_thumbnail(url="https:{}".format(pokeDict["img"]))
    pokeEmbed.set_footer(text="Source: https://bulbapedia.bulbagarden.net/")
    return pokeEmbed
      
  async def getPokeURLs(self, session):
    """Create a dictionary containing the Bulbapedia URLs for every Pokemon."""
    baseURL = "http://bulbapedia.bulbagarden.net"
    pokeURL = "{}{}".format(baseURL, "/wiki/List_of_Pok%C3%A9mon_by_National_Pok%C3%A9dex_number")
    self.pokedex = dict()
    async with session.get(pokeURL) as response:
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
              # tempDict= dict()
              # tempDict["url"] = baseURL + url
              self.pokedex[pokemon] = "{}{}".format(baseURL, url)
      # It's not a table that we're interested in
      else:
        continue
    return
    
  @commands.command()
  async def pokemon(self, *search : str):
    """Look up a Pokemon on Bulbapedia"""
    errorMsg = ["Invalid Pokemon '{}' specified.".format(" ".join(search)),
                "Please specify a valid Pokemon to look up."]
    if (len(search) < 1):
      await self.bot.say("```{0[1]}```".format(errorMsg))
      return
    # Share a client session so it will not open a new session for each request
    async with aiohttp.ClientSession() as session:
      # Setup the dictionary with all of the URL's first
      if (self.pokedex == None):
        await self.getPokeURLs(session)
      species = "_".join(search).lower()
      species = species.replace("mega_", "")
      url     = ""
      pokemon = ""
      if (species in self.pokedex):
        pokemon = species
      elif (species == "derpkip"):
        pokemon = "mudkip"
      elif (species == "farfetchd"):
        pokemon = "farfetch'd"
      elif (species == "flabebe"):
        pokemon = "flabébé"
      elif (species == "type_null"):
        pokemon = "type:_null"
      elif (species == "nidoran"):
        await self.bot.say("""```Please specify either Nidoran (F) or Nidoran \
(M).```""")
        return
      elif (species in ("nidoran_f", "nidoran_m")):
        pokemon = "nidoran_(f)" if species.endswith("f") else "nidoran_(m)"
      else:
        await self.bot.say("```{0[0]} {0[1]}```".format(errorMsg))
        return
      # Get the Bulbapedia URL
      url = self.pokedex[pokemon]
      # Get the Bulbapedia page
      async with session.get(url) as response:
        try:
          assert(response.status == 200)
          data = await response.read()
        except Exception as e:
          logging.error(e)
          return
    # Get a BeautifulSoup object
    try:
      soup = BeautifulSoup(data, "html.parser")
    except Exception as e:
      logging.error(e)
      return
    # Get the Pokemon's information from the BeautifulSoup object
    pokeDict  = self.getPokeData(soup, pokemon)
    if (not pokeDict):
      logging.error("""Something went wrong while getting data from the \
BeautifulSoup object for the Pokemon '{}'.""".format(pokemon))
      return
    pokeEmbed = self.getPokeEmbed(pokeDict, pokemon)
    await self.bot.say(embed=pokeEmbed)
    return