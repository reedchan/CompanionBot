#!/usr/bin/env python3
# Python standard modules
import argparse
import configparser
import json
import logging
import os
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
# What the bot is playing/streaming
botGameStatus.name  = "CompanionBot at github.com/reedchan/CompanionBot"
# 0 for playing, 1 for streaming
botGameStatus.type  = 0

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

def main():
  global bot
  logFormat   = "{asctime}  {levelname:<10} {message}"
  dateFormat  = "%Y-%m-%d %H:%M:%S UTC-%z"
  logging.basicConfig(format=logFormat, datefmt=dateFormat, level=logging.INFO,
                      style="{")
  parser = argparse.ArgumentParser()
  parser.add_argument("-c", "--config",
                      help="use settings in configFile",
                      action="store_true")  
  parser.add_argument("--token",
                      help="specify the bot's token to run it",
                      type=str)
  parser.add_argument("-v", "--verbose",
                      help="change the logging level to DEBUG",
                      action="store_true")
  parser.add_argument("--music",
                      help="add music playback functionality to the bot",
                      action="store_true")
  parser.add_argument("--pokemon",
                      help="add Bulbapedia Pokemon lookup functionality to the bot",
                      action="store_true")
  parser.add_argument("--terraria",
                      help="add Terraria prefix ID lookup functionality to the bot",
                      action="store_true")
  args = parser.parse_args()
  config = configparser.ConfigParser()
  # Directory that this file is in
  botDir      = path.split(__file__)[0]
  # Config file
  configFile  = path.join(botDir, "botConfig.ini")
  if (not path.exists(configFile)):
    config["DEFAULT"] = {}
    config["DEFAULT"]["token"]    = str(args.token)
    config["DEFAULT"]["verbose"]  = str(args.verbose)
    config["COGS"] = {}
    config["COGS"]["music"]     = str(args.music)
    config["COGS"]["pokemon"]   = str(args.pokemon)
    config["COGS"]["terraria"]  = str(args.terraria)
    try:
      with open(configFile, 'w') as f:
        config.write(f)
    except Exception as e:
      logging.error(e)
      sys.exit(1)
  if (args.config):
    try:
      assert(path.exists(configFile))
    except AssertionError:
      logging.error("{} does not exist.".format(configFile))
      sys.exit(1)
    try:
      config.read(configFile)
    except Exception as e:
      logging.error(e)
      sys.exit(1)

  if (args.verbose or (args.config and config["DEFAULT"].getboolean("verbose"))):
    logging.getLogger().setLevel(logging.DEBUG)
  if (args.music or (args.config and config["COGS"].getboolean("music"))):
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
  if (args.pokemon or (args.config and config["COGS"].getboolean("pokemon"))):
    try:
      from pokemon import Pokemon
      bot.add_cog(Pokemon(bot))
    except Exception as e:
      logging.error(e)
      sys.exit(1)
  if (args.terraria or (args.config and config["COGS"].getboolean("terraria"))):
    try:
      from terraria import Terraria
      bot.add_cog(Terraria(bot))
    except Exception as e:
      logging.error(e)
      sys.exit(1)
  if (args.config):
    token = config["DEFAULT"]["token"]
  else:
    token = args.token
  try:
    assert(token and (token != "None"))
    bot.run(token)
  except AssertionError:
    if (args.config):
      logging.error("Invalid token '{}' in {}".format(token, configFile))
    else:
      logging.error("""Invalid token '{}' specified. Please use {} or specify \
a token.""".format(token, configFile))
    sys.exit(1)
  except Exception as e:
    logging.error(e)
    sys.exit(1)
  return

if __name__ == '__main__':
  main()