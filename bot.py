import discord
import json
import random
from discord.ext import commands
from sys import argv

description = '''An example bot to showcase the discord.ext.commands extension
module.
There are a number of utility commands being showcased here.'''
bot = commands.Bot(command_prefix='!', description=description)
prefixDict = None

@bot.event
async def on_ready():
    print('Logged in as')
    print(bot.user.name)
    print(bot.user.id)
    print('------')

@bot.command(pass_context=True)
async def add(ctx, left : int, right : int):
    """Adds two numbers together."""
    await bot.say("%d + %d = %d" % (left, right, left + right))

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

@bot.command(description='For when you wanna settle the score some other way')
async def choose(*choices : str):
    """Chooses between multiple choices."""
    await bot.say(random.choice(choices))

@bot.command()
async def repeat(times : int, content='repeating...'):
    """Repeats a message multiple times."""
    for i in range(times):
        await bot.say(content)

@bot.command()
async def joined(member : discord.Member):
    """Says when a member joined."""
    await bot.say('{0.name} joined in {0.joined_at}'.format(member))

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
async def terraria(search: str):
  prefix = search.lower()
  if (prefix in prefixDict):
    id = prefixDict[prefix]
    if (prefix in ("deadly", "hasty", "quick")):
      await bot.say("```%s: %s, %s```" % (prefix, id[0], id[1]))
    else:
      await bot.say("```%s: %s```" % (prefix, id))
  else:
    await bot.say("```Please specify the prefix you would like to look up.```")

def main(argv):
  global prefixDict
  try:
    f = open("terrariaPrefixes.json", 'r')
    prefixDict = json.loads(f.read())
    f.close()
  except Exception as e:
    print(e)
    sys.exit(1)
  try:
    assert(len(argv) > 1)
  except AssertionError:
    print("Please specify the bot's token as an argument.")
    sys.exit(1)
  bot.run(argv[1])

if __name__ == '__main__':
  main(argv)