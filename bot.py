import discord
import json
import random
import re

from discord.ext import commands
from sys import argv, exit

# Import the music features
from playlist import Music, VoiceEntry, VoiceState

description = """\
A rudimentary bot based on discord.py's basic_bot.py and discord.py's \
playlist.py. Please report any issues at https://github.com/reedchan/companionbot\
"""
bot = commands.Bot(command_prefix=commands.when_mentioned_or("!"),
                   description=description)
bot.add_cog(Music(bot))
botGameStatus       = discord.Game()
botGameStatus.name  = "CompanionBot at github.com/reedchan/CompanionBot"
nationalDex = dict()
prefixDict  = dict()

if not discord.opus.is_loaded():
    # the 'opus' library here is opus.dll on windows
    # or libopus.so on linux in the current directory
    # you should replace this with the location the
    # opus library is located in and with the proper filename.
    # note that on windows this DLL is automatically provided for you
    discord.opus.load_opus('opus')

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
  global nationalDex, prefixDict
  nationalDex = loadDict("pokedex.json")
  prefixDict  = loadDict("terrariaPrefixes.json")
  try:
    assert(len(argv) > 1)
  except AssertionError:
    print("Please specify the bot's token as an argument.")
    exit(1)
  try:
    bot.run(argv[1])
  except Exception as e:
    print(e)
    exit(1)

if __name__ == '__main__':
  main(argv)