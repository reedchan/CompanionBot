#!/usr/bin/env python3
# Python standard modules
import getopt
import json
import logging
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
Usage: {} [options...]
  -h, --help        Print this help message
  -t, --token       Specify the bot's token to run it
  -v, --verbose     Change the logging level to DEBUG
      --music       Add music playback functionality to the bot
      --pokemon     Add Bulbapedia Pokemon lookup functionality to the bot
      --terraria    Add Terraria prefix ID lookup functionality to the bot
""".format(path.split(__file__)[1])
  print(info)
  sys.exit(returnCode)
  
@bot.event
async def on_ready():
    logging.info('Logged in as')
    logging.info(bot.user.name)
    logging.info(bot.user.id)
    logging.info('------')
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
  shortOpts = "ht:v"
  longOpts = ["help", "token=", "verbose",
              "music", "pokemon", "terraria"]
  token = ""
  try:
    opts, args = getopt.getopt(argv, shortOpts, longOpts)
  except getopt.GetoptError as e:
    logging.error(e)
    help(2)
  for (o, a) in opts:
    if (o in ("-h", "--help")):
      help(2)
    elif (o in ("-t", "--token")):
      token = a
    elif (o in ("-v", "--verbose")):
      logging.getLogger().setLevel(logging.DEBUG)
    elif (o == "--music"):
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
    elif (o == "--pokemon"):
      try:
        from pokemon import Pokemon
        bot.add_cog(Pokemon(bot))
      except Exception as e:
        logging.error(e)
        sys.exit(1)
    elif (o == "--terraria"):
      try:
        from terraria import Terraria
        bot.add_cog(Terraria(bot))
      except Exception as e:
        logging.error(e)
        sys.exit(1)
  try:
    bot.run(token)
  except Exception as e:
    logging.error(e)
    sys.exit(1)
  return

if __name__ == '__main__':
  main(sys.argv[1:])