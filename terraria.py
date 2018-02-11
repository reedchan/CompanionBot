# Standard Python modules
import logging
# Non-standard Python modules
import aiohttp
import discord
from bs4 import BeautifulSoup
from discord.ext import commands

user_agent = 'Mozilla/5.0 (Windows; U; Windows NT 10.0; rv:10.0) Gecko/20100101 Firefox/52.0'
sendHeader = {'UserAgent':user_agent,}

class Terraria:
  """Terraria-related commands."""
  def __init__(self, bot):
    self.bot = bot
    self.prefixes = None

  async def _getTPrefixes(self, session):
    """Create a dictionary containing the ID's for each Terraria prefix."""
    url = "http://terraria.gamepedia.com/Prefix_IDs"
    async with session.get(url) as response:
      try:
        assert(response.status == 200)
        data = await response.read()
        soup = BeautifulSoup(data, "html.parser")
      except Exception as e:
        logging.error(e)
        return False
    d = dict()
    tables = soup.find_all(name="table")
    for tableBody in tables:
      # Select the correct table
      if (tableBody.attrs == {"class": ["terraria", "sortable"]}):
        rows = tableBody.find_all(name="tr")
        for row in rows:
          cols = row.find_all(name="td")
          if (len(cols) == 2):
            prefix = cols[0].string.lower().strip()
            id     = cols[1].string.lower().strip()
            #Prefix that has multiple IDs
            if (prefix in d):
              d[prefix] = [d[prefix], id]
            else:
              d[prefix] = id
    self.prefixes = d
    return

  @commands.command()
  async def prefix(self, ctx, search : str):
    """Look up an item prefix on the official Terraria wiki."""
    if (search == ""):
      await ctx.send("Please specify a Terraria prefix to look up.")
      return
    # Share a client session so it will not open a new session for each request
    async with aiohttp.ClientSession() as session:
      # Setup the dictionary with all of the prefixes first
      if (self.prefixes == None):
        await self._getTPrefixes(session)
    prefix = search.lower()
    if (prefix in self.prefixes):
      id = self.prefixes[prefix]
      # Prefix with multiple IDs
      if (type(id) == list):
        await ctx.send("```{0}: {1}```".format(prefix, ", ".join(id)))
      else:
        await ctx.send("```{0}: {1}```".format(prefix, id))
    else:
      await ctx.send("""```Invalid prefix '{}' specified. Please specify \
a valid prefix to look up```.""".format(search))
    return