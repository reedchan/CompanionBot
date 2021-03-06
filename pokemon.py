# TODO: FIX INDENTATION TO REMOVE THIS ERROR
#       PEP8-COMPLIANT MEANS 4 SPACES/TAB
import logging
import re

import aiohttp
import discord
from bs4 import BeautifulSoup
from discord.ext import commands
from asyncTest import saveDict

user_agent = """\
Mozilla/5.0 (Windows; U; Windows NT 10.0; rv:10.0) Gecko/20100101 Firefox/52.0\
"""
sendHeader = {'User-Agent': user_agent, }


class Pokemon:
    """Pokemon related commands."""
    def __init__(self, bot):
        self.bot = bot
        self.pokedex = None

    def _getPokeCategory(self, tble, poke):
        """Get a Pokemon's category from its Bulbapedia page.

        Keyword arguments:
        tble -- the info table from the BeautifulSoup object of the page
        poke -- the name of the Pokemon
        """
        try:
            pokeText = tble.find(name="a",
                                 title=re.compile("Pok.mon category"))
            # If the Pokemon category has an explanation
            # i.e. if you hover over it
            if (pokeText.string is None):
                pokeText = pokeText.find(name="span",
                                         attrs={"class": "explain"})
            pokeText = pokeText.string
            # "é" = "\u00e9"
            if (" Pok\u00e9mon" not in pokeText):
                pokeText = "{} Pok\u00e9mon".format(pokeText)
        except Exception as e:
            logging.error(e)
            logging.error("Error getting Pokemon category for {}".format(poke))
            return False
        return pokeText

    def _getPokeNatDexNo(self, tble, poke):
        """Get a Pokemon's National Dex number from its Bulbapedia page.

        Keyword arguments:
        tble -- the info table from the BeautifulSoup object of the page
        poke -- the name of the Pokemon
        """
        dexRE = re.compile("List of Pok.mon by National Pok.dex number")
        try:
            natDexNo = tble.find(name="a", title=dexRE).string
            assert(natDexNo != "")
        except Exception as e:
            logging.error(e)
            logging.error("""\
Error getting National Pokedex number for {}\
""".format(poke))
            return False
        return natDexNo

    def _getPokeEmbedImg(self, tble, poke):
        """Get a Pokemon's image URL from its Bulbapedia page.

        Keyword arguments:
        tble -- the info table from the BeautifulSoup object of the page
        poke -- the name of the Pokemon
        """
        try:
            embedImg = tble.find(name="a", attrs={"class": "image"})
            embedImg = embedImg.find(name="img")
            embedImg = embedImg.get("src")
        except Exception as e:
            logging.error(e)
            logging.error("Error getting embed image for {}".format(poke))
            return False
        embedImg = "https:{}".format(embedImg)
        return embedImg

    # TODO: LOOK INTO USING COLLECTIONS.ORDEREDDICT INSTEAD OF DICT FOR TYPES,
    #       ABILITIES, AND BASE STATSs
    def _getPokeTypes(self, tble, poke):
        """Get a Pokemon's types from its Bulbapedia page.

        Keyword arguments:
        tble -- the info table from the BeautifulSoup object of the page
        poke -- the name of the Pokemon
        """
        pokeTypes = dict()
        typeRE = re.compile("(?<!Unknown )\(type\)")
        typeSet = []
        try:
            types = tble.find_all(name="a", title=typeRE)
            for type in types:
                tempTable = type.find_parent("table")
                add = True
                for setTable in typeSet:
                    # TODO: LOOK INTO THE POSSIBILITY OF OPTIMIZING W/ SETS
                    if (tempTable is setTable):
                        add = False
                if (add):
                    typeSet += [tempTable]
            while(len(typeSet) > 0):
                typeTable = typeSet.pop()
                parent = typeTable.find_parent(name="td")
                key = parent.find(name="small")
                if (key is not None):
                    key = key.string
                else:
                    key = poke
                for type in typeTable.find_all(name="a", title=typeRE):
                    if (key in pokeTypes):
                        # pokeTypes[key] = pokeTypes[key] + ";" + type.string
                        pokeTypes[key] = "{};{}".format(pokeTypes[key],
                                                        type.string)
                    else:
                        pokeTypes[key] = type.string
        except Exception as e:
            logging.error(e)
            logging.error("Error getting types for {}".format(poke))
            return False
        return pokeTypes

    def _getPokeAbilities(self, tble, poke):
        """Get a Pokemon's abilities from its Bulbapedia page.

        Keyword arguments:
        tble -- the info table from the BeautifulSoup object of the page
        poke -- the name of the Pokemon
        """
        abilities = dict()
        try:
            # Find the link in the table for abilities
            abilityLink = tble.find(name="a", title="Ability")
            assert(abilityLink is not None)
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
                        # Subtitles
                        # e.g. "Hidden Ability", "Mega Charizard X", etc.
                        key = ability.small.string.strip()
                    # No subtitle
                    # Implies that it's a normal ability so use the Pokemon
                    except Exception:
                        key = poke
                        # Pokemon may have multiple possible abilities
                        # e.g. Snorlax may normally have Immunity or Thick Fat
                    for link in ability.find_all(name="a"):
                        if (key in abilities):
                            abilities[key] = "{};{}".format(abilities[key],
                                                            link.string)
                        else:
                            abilities[key] = link.string
        except Exception as e:
            logging.error(e)
            logging.error("Error getting abilities for {}".format(poke))
            return False
        return abilities

    def _getPokeBaseStats(self, soup, poke):
        """Get a Pokemon's base stats from its Bulbapedia page.

        Keyword arguments:
        soup -- the BeautifulSoup object of the Pokemon's page
        poke -- the name of the Pokemon
        """
        baseStats = dict()
        try:
            statTables = soup.find_all(name="table", align="left")
            for table in statTables:
                if (table.span.string != "Stat"):
                    continue
                title = table.find_previous().string
                if (title == "Base stats"):
                    title = poke
                tempDict = dict()
                # Get the tag with the numbers for a stat
                baseStat = table.find_next(name="td")
                # Get the tag with the stat range at level 50
                range50 = baseStat.find_next(name="small")
                # Get the stat range at level 100
                range100 = range50.find_next(name="small").string
                # Get the stat range at level 50
                range50 = range50.string

                def getNextNext(tag, name, string=False):
                    """Get the next next name element from the tag.

                    Optional: return the element's string

                    Keyword arguments:
                    tag    -- the Beautiful Soup object to work with
                    name   -- the element to get
                    string -- whether or not to return the element's string
                    """
                    temp = tag.find_next(name=name).find_next(name=name)
                    if (string is True):
                        try:
                            temp = temp.string.strip()
                        except Exception as e:
                            logging.error(e)
                    return temp

                key = baseStat.a.string
                tempDict[key] = """\
{};{};{}""".format(getNextNext(baseStat, "th", True), range50, range100)
                # Do this 5 more times (total of 6) to get all of the stats
                for i in range(0, 5):
                    baseStat = getNextNext(baseStat, "td")
                    range50 = baseStat.find_next(name="small")
                    range100 = range50.find_next(name="small").string
                    range50 = range50.string
                    key = baseStat.a.string
                    tempDict[key] = """\
{};{};{}""".format(getNextNext(baseStat, "th", True), range50, range100)
                baseStat = getNextNext(baseStat, "td")
                tempDict["Total"] = getNextNext(baseStat, "th", True)
                baseStats[title] = tempDict
        except Exception as e:
            logging.error(e)
            logging.error("Error getting base stats for {}".format(poke))
            return False
        return baseStats

    def _getPokeData(self, soup, poke):
        """Get a Pokemon's data from its Bulbapedia page.

        Keyword arguments:
        soup -- the BeautifulSoup object of the Pokemon's page
        poke -- the name of the Pokemon
        """
        # Dictionary with the Pokemon's info
        pokeDict = dict()
        infoTable = soup.find(name="table", style=re.compile("float:right*"))
        pokemon = self._titlecase(poke.replace("_", " "))
        # Pokemon info in order of appearance on the Bulbapedia page
        pokeText = ""      # Pokemon text e.g. "Seed Pokemon" for Bulbasaur
        natDexNo = ""      # National Pokédex number
        embedImg = ""      # Image of the Pokemon
        pokeTypes = dict()  # Pokemon types
        abilities = dict()  # Pokemon abilities
        baseStats = dict()  # Pokemon base stats
        pokeText = self._getPokeCategory(tble=infoTable, poke=pokemon)
        natDexNo = self._getPokeNatDexNo(tble=infoTable, poke=pokemon)
        embedImg = self._getPokeEmbedImg(tble=infoTable, poke=pokemon)
        pokeTypes = self._getPokeTypes(tble=infoTable, poke=pokemon)
        abilities = self._getPokeAbilities(tble=infoTable, poke=pokemon)
        baseStats = self._getPokeBaseStats(soup=soup, poke=pokemon)
        pokeDict["category"] = pokeText
        pokeDict["natDexNo"] = natDexNo
        pokeDict["img"] = embedImg
        pokeDict["types"] = pokeTypes
        pokeDict["abilities"] = abilities
        pokeDict["baseStats"] = baseStats
        # Check that there were no problems getting the stats
        # The helper functions return False if there were any issues
        for key in pokeDict:
            if (not pokeDict[key]):
                return False
        return pokeDict

    def _createDiscordEmbed(self, info, poke):
        """Create a formatted Discord Embed object for a Pokemon.

        Keyword arguments:
        info -- the dictionary containing the Pokemon's information
        poke -- the name of the Pokemon
        """
        pokeName = self._titlecase(poke.replace("_", " "))

        def unicodeFix(str):
            """Replace certain substrings with Unicode characters.

            Return a copy of str with certain substrings replaced with Unicode
            characters.
            Keyword arguments:
            str -- the string to copy and modify
            """
            temp = re.sub("[ _]\([fF]\)", "\u2640", str)
            temp = re.sub("[ _]\([mM]\)", "\u2642", temp)
            return temp

        pokeName = unicodeFix(pokeName)
        embed = discord.Embed(title=pokeName,
                              description="{}: {}".format(info["natDexNo"],
                                                          info["category"]),
                              url=self.pokedex[poke])
        types = info["types"]
        abilities = info["abilities"]
        baseStats = info["baseStats"]

        def addField(fieldDict: dict, name: str, inline: bool=False):
            """Add a field to the embed containing the items in the dict.

            Keyword arguments:
            fieldDict -- the dictionary to iterate over
            name      -- the name of the embed field
            inline    -- whether or not the embed field is inline
            """
            strList = []
            if (len(fieldDict) == 1):
                strList.append(list(fieldDict.values())[0].replace(";", ", "))
            else:
                for item in sorted(fieldDict.items()):
                    strList.append("{}: {}".format(item[0],
                                                   item[1].replace(";", ", ")))
            embed.add_field(name=name,
                            value="\n".join(strList),
                            inline=inline)

        addField(types, "Types", inline=False)
        addField(abilities, "Abilities", inline=False)

        statStr = []
        statStr.append("```{:^15}{:^24}".format("Stat", "Range"))
        statStr.append("{:15}{:^12}{:^12}".format("",
                                                  "At Lv. 50", "At Lv. 100"))

        def getValues(poke, stat):
            """Return a list of values for a Pokemon's stat.

            Keyword arguments:
            poke -- the name of the Pokemon
            stat -- the stat to get
            """
            return baseStats[poke][stat].split(";")

        def appendStat(poke, stat):
            """Append a formatted str of a Pokemon's stat to the stat list.

            Keyword arguments:
            poke -- the name of the Pokemon
            stat -- the stat to get
            """
            tempStr = "{}:".format(stat)
            if (stat.lower() != "total"):
                formatStr = "{0:<9}{1[0]:<6}{1[1]:^12}{1[2]:^12}"
            else:
                formatStr = "{0:<9}{1[0]}"
            statStr.append(formatStr.format(tempStr, getValues(poke, stat)))
            return

        keys = sorted(baseStats.keys())
        # Experienced errors with Deoxys probably because of the many forms
        # Limit the base stats to reduce the character count
        # Probably hitting the character limit
        # Limit to 3 tables of stats
        # TODO: REMOVE LIMIT IF THE CHARACTER LIMIT IS UPPED OR REMOVED
        count = 0
        for key in keys:
            if (count == 3):
                break
            statStr.append(unicodeFix(key))
            appendStat(key, "HP")
            appendStat(key, "Attack")
            appendStat(key, "Defense")
            appendStat(key, "Sp.Atk")
            appendStat(key, "Sp.Def")
            appendStat(key, "Speed")
            appendStat(key, "Total")
            count += 1
        statStr.append("```")
        embed.add_field(name="Base Stats",
                        value="\n".join(statStr),
                        inline=False)
        embed.set_thumbnail(url=info["img"])
        embed.set_footer(text="Source: https://bulbapedia.bulbagarden.net")
        return embed

    def _titlecase(self, string):
        """Titlecase workaround for a string with apostrophes.

        Keyword arguments:
        string -- the string to titlecase
        """
        if (string.lower() == "ho-oh"):
            return "Ho-Oh"
        else:
            return " ".join(map(lambda s: s.capitalize(), string.split(" ")))

    async def _getPokeURLs(self, session):
        """Create a dictionary containing the Bulbapedia URLs for every Pokemon.

        Keyword arguments:
        session -- the aiohttp session to use
        """
        baseURL = "http://bulbapedia.bulbagarden.net"
        page = "/wiki/List_of_Pok%C3%A9mon_by_National_Pok%C3%A9dex_number"
        pokeUrl = "{}{}".format(baseURL, page)
        pokedex = dict()
        async with session.get(pokeUrl) as response:
            try:
                assert(response.status == 200)
                data = await response.read()
                soup = BeautifulSoup(data, "html.parser")
            except Exception as e:
                logging.error(e)
        # Add more regions as needed
        regions = {"Kanto",
                   "Johto",
                   "Hoenn",
                   "Sinnoh",
                   "Unova",
                   "Kalos",
                   "Alola",
                   }
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
                        URL = link.get("href")
                        if (("Pok%C3%A9mon" in URL) and
                            ("list" not in URL)):
                            URL = URL.replace("%27", "'")
                            URLRE = re.compile("(/wiki/)|(_\(pok%c3%a9mon\))",
                                               re.IGNORECASE)
                            pokemon = re.sub(URLRE, "", URL)
                            # Farfetch'd
                            pokemon = pokemon.replace("%27", "'")
                            # Nidorans
                            pokemon = pokemon.replace("%e2%99%80", "_(f)")
                            pokemon = pokemon.replace("%e2%99%82", "_(m)")
                            # Flabébé
                            pokemon = pokemon.replace("%c3%a9", "é")
                            pokemon = pokemon.lower()
                            pokedex[pokemon] = "{}{}".format(baseURL, URL)
        self.pokedex = pokedex
        saveDict(pokedex, "asyncPokedex.json", "")
        return

    @commands.command()
    async def pokemon(self, ctx, *search: str):
        """Look up a Pokemon on Bulbapedia"""
        errorMsg = ["Invalid Pokemon '{}' specified.".format(" ".join(search)),
                    "Please specify a valid Pokemon to look up."]
        if (len(search) < 1):
            await ctx.send("```{0[1]}```".format(errorMsg))
            return
        # Share a client session so it will not open a new session for each request
        async with aiohttp.ClientSession() as session:
            # Setup the dictionary with all of the URL's first
            if (self.pokedex is None):
                await self._getPokeURLs(session)
            species = "_".join(search).lower()
            species = species.replace("mega_", "")
            URL = ""
            pokemon = ""
            # TODO: LOOK INTO MAKING THESE DICTIONARY ENTRIES INSTEAD OF CONDITIONALS
            if (species in self.pokedex):
                pokemon = species
            elif (species == "derpkip"):
                pokemon = "mudkip"
            elif (species == "farfetchd"):
                pokemon = "farfetch'd"
            elif (species == "flabebe"):
                pokemon = "flabébé"
            elif ((species == "hakamoo") or (species == "hakamo_o")):
                pokemon = "hakamo-o"
            elif ((species == "ho_oh") or (species == "hooh")):
                pokemon = "ho-oh"
            elif ((species == "jangmoo") or (species == "jangmo_o")):
                pokemon = "jangmo-o"
            elif ((species == "kommoo") or (species == "kommo_o")):
                pokemon = "kommo-o"
            elif (species == "mime_jr"):
                pokemon = "mime_jr."
            elif (species == "mr_mime"):
                pokemon = "mr._mime"
            elif ((species == "porygon_z") or (species == "porygonz")):
                pokemon = "porygon-z"
            elif (species == "type_null"):
                pokemon = "type:_null"
            elif (species == "nidoran"):
                await ctx.send("""```Please specify either Nidoran (F) or\
 Nidoran (M).```""")
                return
            elif (species == "nidoran_f"):
                pokemon = "nidoran_(f)"
            elif (species == "nidoran_m"):
                pokemon = "nidoran_(m)"
            else:
                await ctx.send("```{0[0]} {0[1]}```".format(errorMsg))
                return
            # Get the Bulbapedia URL
            URL = self.pokedex[pokemon]
            # Get the Bulbapedia page
            async with session.get(URL) as response:
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
        pokeDict = self._getPokeData(soup, pokemon)
        if (not pokeDict):
            logging.error("""Something went wrong while getting data from the \
BeautifulSoup object for the Pokemon '{}'.""".format(pokemon))
            return
        pokeEmbed = self._createDiscordEmbed(pokeDict, pokemon)
        await ctx.send(embed=pokeEmbed)
        return
