import discord
import getopt
import json
import random
import re

from discord.ext import commands
from os import path
from sys import argv, exit

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
  -m, --music       Add music playback functionality to the bot
  -t, --token       Specify the bot's token to run it
""" % path.split(__file__)[1]
  print(info)
  exit(returnCode)

@bot.event
async def on_ready():
    print('Logged in as')
    print(bot.user.name)
    print(bot.user.id)
    print('------')
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
async def pokemon(*search: str):
  """Get info about a Pokémon."""
  species = "_".join(search).lower()
  species = species.replace("mega_", "")
  if (species in nationalDex):
    # await bot.say("```%s```" % nationalDex[species])
    await bot.say("%s" % nationalDex[species])
  # For people who are too lazy to type the apostrophe
  elif (species == "farfetchd"):
    await bot.say("%s" % nationalDex["farfetch'd"])
  # Simplify searching for Flabébé
  elif (species == "flabebe"):
    await bot.say("%s" % nationalDex["flabébé"])
    # await bot.say("%s" % nationalDex["flab\u00e9b\u00e9"])
  # For people who are too lazy to type the colon
  elif (species == "type_null"):
    await bot.say("%s" % nationalDex["type:_null"])
  # Specify Nidoran (M) or (F)
  elif (species == "nidoran"):
    await bot.say("```Please specify 'nidoran (f)' or 'nidoran (m)'```")
    
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
async def terraria(search: str):
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
    print(e)
    exit(1)
  return d

def main(argv):
  global bot, nationalDex, prefixDict
  shortOpts = "hmt:"
  longOpts = ["help", "music", "token="]
  token = ""
  try:
    opts, args = getopt.getopt(argv[1:], shortOpts, longOpts)
  except Exception as e:
    print(e)
    help(2)
  for (o, a) in opts:
    if (o in ("-h", "--help")):
      help(2)
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
        print(e)
        exit(1)
    elif (o in ("-t", "--token")):
      token = a
  try:
    assert(token != "")
  except AssertionError:
    print("Please specify the bot's token as an argument.")
    exit(1)
  except Exception as e:
    print(e)
    exit(1)
  nationalDex = loadDict("pokedex.json")
  prefixDict  = loadDict("terrariaPrefixes.json")
  try:
    bot.run(token)
  except Exception as e:
    print(e)
    exit(1)
  return

if __name__ == '__main__':
  main(argv)