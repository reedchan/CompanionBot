#!/usr/bin/env python3
# Python standard modules
import getopt
import json
import logging
import pprint
import random
import re
import sys
from os import path
# Non-standard modules
import discord
from discord.ext import commands

description = """\
A rudimentary bot based on discord.py's basic_bot.py and discord.py's \
playlist.py. Please report any issues at https://github.com/reedchan/companionbot\
"""
bot = commands.Bot(command_prefix=commands.when_mentioned_or("!"),
                   description=description)
botGameStatus       = discord.Game()
botGameStatus.name  = "CompanionBot at github.com/reedchan/CompanionBot"
nationalDex = dict()
prefixDict  = dict()

def help(returnCode):
  info = """\
Usage: %s [options...]
  -h, --help        Print this help message
  -t, --token       Specify the bot's token to run it
  -v, --verbose     Change the logging level to DEBUG
  -m, --music       Add music playback functionality to the bot
""" % path.split(__file__)[1]
  print(info)
  sys.exit(returnCode)
  
def getPokeEmbed(species):
  pokeDict    = nationalDex[species]
  pokeName    = list(map(lambda x:x.capitalize(), species.split("_")))
  pokeName    = " ".join(pokeName)
  prettyName  = pokeName.replace("(m)", "\u2642").replace("(f)", "\u2640")
  pokeEmbed = discord.Embed(title=prettyName,
                            description="{}: {}".format(pokeDict["natDexNo"],
                                                        pokeDict["category"]),
                            url=pokeDict["url"])
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

@bot.event
async def on_ready():
    logging.debug('Logged in as')
    logging.debug(bot.user.name)
    logging.debug(bot.user.id)
    logging.debug('------')
    await bot.change_presence(game=botGameStatus, afk=False)
    
# The order of the @bot.command functions determines their order in the help msg

@bot.command(pass_context=True)
async def add(ctx, left : int, right : int):
    """Adds two numbers together."""
    await bot.say("%d + %d = %d" % (left, right, left + right))
    
@bot.command(description='For when you wanna settle the score some other way')
async def choose(*choices : str):
    """Chooses between multiple choices."""
    await bot.say(random.choice(choices))
    
@bot.group(pass_context=True)
async def cool(ctx):
    """Says if a user is cool.
    In reality this just checks if a subcommand is being invoked.
    """
    if ctx.invoked_subcommand is None:
        await bot.say('No, {0.subcommand_passed} is not cool'.format(ctx))

@cool.command(name='bot')
async def _bot():
    """Is the bot cool?"""
    await bot.say('Yes, the bot is cool.')
    
@bot.command()
async def joined(member : discord.Member):
    """Says when a member joined."""
    await bot.say('{0.name} joined in {0.joined_at}'.format(member))
    
@bot.command()
async def pokemon(*search : str):
  """Get info about a Pokémon."""
  species = "_".join(search).lower()
  species = species.replace("mega_", "")
  if (species in nationalDex):
    # await bot.say("```%s```" % nationalDex[species])
    # await bot.say("%s" % nationalDex[species])
    await bot.say(embed=getPokeEmbed(species))
  # For people who are too lazy to type the apostrophe
  elif (species == "farfetchd"):
    # await bot.say("%s" % nationalDex["farfetch'd"])
    await bot.say(embed=getPokeEmbed("farfetch'd"))
  # Simplify searching for Flabébé
  elif (species == "flabebe"):
    # await bot.say("%s" % nationalDex["flabébé"])
    await bot.say(embed=getPokeEmbed("flabébé"))
    # await bot.say("%s" % nationalDex["flab\u00e9b\u00e9"])
  # For people who are too lazy to type the colon
  elif (species == "type_null"):
    # await bot.say("%s" % nationalDex["type:_null"])
    await bot.say(embed=getPokeEmbed("type:_null"))
  # Specify Nidoran (M) or (F)
  elif (species == "nidoran"):
    await bot.say("```Please specify 'nidoran (f)' or 'nidoran (m)'```")
  elif (species in ("nidoran_f", "nidoran_m")):
    await bot.say(embed=getPokeEmbed(species.replace("f", "(f)").replace("m", "(m)")))
  elif (species == "derpkip"):
    await bot.say(embed=getPokeEmbed("mudkip"))
  else:
    await bot.say("```Please specify the Pokémon you would like to look up.```")
    
# content defaults to the string "repeating..."
@bot.command()
async def repeat(times : int, content='repeating...'):
    """Repeats a message multiple times."""
    for i in range(times):
        await bot.say(content)

@bot.command()
async def roll(dice : str):
    """Rolls a dice in NdN format."""
    try:
        rolls, limit = map(int, dice.split('d'))
    except Exception:
        await bot.say('Format has to be in NdN!')
        return

    result = ', '.join(str(random.randint(1, limit)) for r in range(rolls))
    await bot.say(result)

@bot.command()
async def terraria(search : str):
  """Get the ID of a Terraria prefix."""
  prefix = search.lower()
  if (prefix in prefixDict):
    id = prefixDict[prefix]
    if (prefix in ("deadly", "hasty", "quick")):
      await bot.say("```%s: %s, %s```" % (prefix, id[0], id[1]))
    else:
      await bot.say("```%s: %s```" % (prefix, id))
  else:
    await bot.say("```Please specify the prefix you would like to look up.```")
    
# Safely load a dictionary that has been saved to readFile, a JSON file, and
# return the dictionary
def loadDict(readFile):
  d = dict()
  try:
    f = open(readFile, 'r')
    d = json.loads(f.read())
    f.close()
  except Exception as e:
    logging.error(e)
    sys.exit(1)
  return d

def main(argv):
  global bot, nationalDex, prefixDict
  logFormat   = "{asctime}  {levelname:<10} {message}"
  dateFormat  = "%Y-%m-%d %H:%M:%S UTC-%z"
  logging.basicConfig(format=logFormat, datefmt=dateFormat, level=logging.INFO,
                      style="{")
  shortOpts = "hmt:v"
  longOpts = ["help", "token=", "verbose",
              "music"]
  token = ""
  try:
    opts, args = getopt.getopt(argv, shortOpts, longOpts)
  except Exception as e:
    logging.error(e)
    help(2)
  for (o, a) in opts:
    if (o in ("-h", "--help")):
      help(2)
    elif (o in ("-t", "--token")):
      token = a
    elif (o in ("-v", "--verbose")):
      logging.getLogger().setLevel(logging.DEBUG)
    elif (o in ("-m", "--music")):
      try:
        # Import the music features
        from playlist import Music, VoiceEntry, VoiceState
        if not discord.opus.is_loaded():
            # the 'opus' library here is opus.dll on windows
            # or libopus.so on linux in the current directory
            # you should replace this with the location the
            # opus library is located in and with the proper filename.
            # note that on windows this DLL is automatically provided for you
            discord.opus.load_opus('opus')
        bot.add_cog(Music(bot))
      except Exception as e:
        logging.error(e)
        sys.exit(1)

  try:
    assert(token != "")
  except AssertionError:
    logging.error("Please specify the bot's token as an argument.")
    sys.exit(1)
  except Exception as e:
    logging.error(e)
    sys.exit(1)
  nationalDex = loadDict("pokedex.json")
  prefixDict  = loadDict("terrariaPrefixes.json")
  try:
    bot.run(token)
  except Exception as e:
    logging.error(e)
    sys.exit(1)
  return

if __name__ == '__main__':
  main(sys.argv[1:])