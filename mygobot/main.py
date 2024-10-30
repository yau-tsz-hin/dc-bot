import discord
import yaml
import json
import os
import glob
import yt_dlp
import asyncio
import random
from discord.ext import commands
from discord import app_commands
from discord.utils import get
import image_map
import imagegetter
import re

# Load settings
with open('config.yml', 'r', encoding='utf8') as configfile:
    SETTINGS = yaml.load(configfile, yaml.Loader)

# Handle settings
if SETTINGS['send-as-attachment'] and SETTINGS['download-files']:
    if not os.path.isdir('./img'):
        try:
            os.mkdir('./img')
        except Exception as e:
            print('Failed to make storage dir, quitting:', e)
            exit()
    
    if SETTINGS['download-at-startup']:
        asyncio.run(imagegetter.download_all())

# Function to reload message mappings
def reload():
    global message_mappings
    with open('mygo.json', 'r', encoding='utf8') as mappingfile:
        message_mappings = json.load(mappingfile)

message_mappings = {}
reload()

# Bot section
with open('token.txt', 'r', encoding='utf8') as tokenfile:
    bot_token = tokenfile.read().strip()

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f"{bot.user} is now running!")
    try:
        files = glob.glob('./audio/*')
        for f in files:
            os.remove(f)
    except Exception as e:
        print(e)
    try:
        syncedCMD = await bot.tree.sync()
        print(f"Synced {len(syncedCMD)} commands")
    except Exception as e:
        print(e)
    await bot.change_presence(
        activity=discord.Activity(name='its code contributor: killicit.wy and andyyau(v2.0)', type=discord.ActivityType.listening)
    )

# Music commands
@bot.tree.command(name='play')
@app_commands.describe(url="Enter the youtube link here")
async def play(ctx: discord.Interaction, url: str):
    player = Player(ctx, url, bot, False)
    await player.start()

@bot.tree.command(name='loop')
@app_commands.describe(url="Enter the youtube link here")
async def loop(ctx: discord.Interaction, url: str):
    player = Player(ctx, url, bot, True)
    await player.start()

@bot.tree.command(name='pause')
async def pause(ctx: discord.Interaction):
    await player.pause()
    await ctx.response.send_message("Paused")

@bot.tree.command(name='resume')
async def resume(ctx: discord.Interaction):
    await player.resume()
    await ctx.response.send_message("Resumed")

@bot.tree.command(name='stop')
async def stop(ctx: discord.Interaction):
    await player.stop()
    await ctx.response.send_message("Stopped")

@bot.event
async def on_message(ctx: discord.Message):
    if ctx.author.bot:
        return

    imgs = set()
    msg = ctx.content.lower()

    # 檢查訊息是否以 '!' 開頭，如果沒有則返回
    if not msg.startswith("!"):
        return

    # 刪除訊息中的 '!' 符號
    msg = msg[1:]  # 移除 '!' 字符

    for key in message_mappings:
        if key in msg:
            value = message_mappings[key]
            imgs.update(value['value'])

    for name in image_map.get_all_names():
        if msg in name:
            imgs.add(name)

    imgs = list(imgs)
    if imgs:
        img = imgs[random.randint(0, len(imgs) - 1)]

        if SETTINGS['send-as-attachment']:
            file = await imagegetter.get_file_handle(img)
            if file is None:
                print(f'Could not send file {img}')
            fileObject = discord.File(file, f'{img}.jpg')
            try:
                await ctx.channel.send(file=fileObject)
            except discord.errors.Forbidden:
                print("Permission denied when attempting to send message")
        else:
            try:
                await ctx.channel.send(imagegetter.get_link(img))
            except discord.errors.Forbidden:
                print("Permission denied when attempting to send message")

    if await bot.is_owner(ctx.author):
        if ctx.content.strip() == "春日影":
            reload()
            print("為什麼要演奏春日影！")


#@bot.event
#async def on_message(ctx: discord.Message):
#    if ctx.author.bot:
#        return
#    imgs = set()
#    msg = ctx.content.lower()
#
#    if not msg:
#        return
#
#
#
#    for key in message_mappings:
#        if key in msg:
#            value = message_mappings[key]
#            imgs.update(value['value'])
#            
#    
#    for name in image_map.get_all_names():
#        if msg in name:
#            imgs.add(name)
#
#    imgs = list(imgs)
#    if imgs:
#        img = imgs[random.randint(0, len(imgs) - 1)]
#        
#        if SETTINGS['send-as-attachment']:
#            file = await imagegetter.get_file_handle(img)
#            if file is None:
#                print(f'Could not send file {img}')
#            fileObject = discord.File(file, f'{img}.jpg')
#            try:
#                await ctx.channel.send(file=fileObject)
#            except discord.errors.Forbidden:
#                print("Permission denied when attempting to send message")
#                
#        else:
#            try:
#                await ctx.channel.send(imagegetter.get_link(img))
#            except discord.errors.Forbidden:
#                print("Permission denied when attempting to send message")
#    
#    if await bot.is_owner(ctx.author):
#        if ctx.content.strip() == "春日影":
#            reload()
#            print("為什麼要演奏春日影！")

# Player class and helper functions
class Player:
    def __init__(self, ctx: discord.Interaction, url: str, bot: commands.Bot, loop=False) -> None:
        self.ctx = ctx
        self.url = url
        self.bot = bot
        self.loop = loop
        self._voice_channel = self.set_voice_channel()
        self.vc = get(bot.voice_clients, guild=ctx.guild)
        self.not_stop = False

    @property
    def voice_channel(self):
        return self._voice_channel
    
    def set_voice_channel(self):
        try:
            self._voice_channel = self.ctx.user.voice.channel
            return self._voice_channel
        except:
            if self.ctx.user.voice is None:
                asyncio.get_event_loop().create_task(self.ctx.followup.send("You need to be in a voice channel to play music"))
                raise Exception("User not in voice channel")
            raise

    async def start(self):
        await self.ctx.response.defer()
        try:
            delete_temp("./audio/*")
            msg = await self.ctx.followup.send(content="Trying to download", wait=True)
            file = download_music(self.url)

            if self.vc and self.vc.is_connected():
                await self.vc.move_to(self.voice_channel)
            else:
                self.vc = await self.voice_channel.connect()

            self.vc.stop()
            await asyncio.sleep(0.1)

            if not self.loop:
                self.vc.play(discord.FFmpegPCMAudio(source=file))
            else:
                self.not_stop = True
                loop_count_msg = await self.ctx.followup.send(content="Loop Count: 0")
                self.vc.play(discord.FFmpegPCMAudio(source=file), after=lambda e: self.vc.client.loop.create_task(self.repeat_play(file, 1, loop_count_msg)))

            await msg.edit(content=f"Playing: {self.url}")

        except Exception as e:
            print(f"Error in Player.start: {e}")
            await self.ctx.followup.send(content="Error")

    async def stop(self):
        self.vc.stop()
        self.not_stop = False

    async def pause(self):
        self.vc.pause()
    
    async def resume(self):
        self.vc.resume()

    async def repeat_play(self, url, count, loop_count_msg):
        while self.not_stop:
            self.vc.play(discord.FFmpegPCMAudio(source=url), after=lambda e: self.vc.client.loop.create_task(self.repeat_play(url, count + 1, loop_count_msg)))
            await loop_count_msg.edit(content=f"Loop count: {count}")

def delete_temp(path: str):
    try:
        files = glob.glob(path)
        for f in files:
            os.remove(f)
    except Exception as e:
        print(e)

def download_music(url):
    ydl_opts = {'outtmpl': "./audio/%(id)s.%(ext)s", 'format': 'bestaudio', 'noplaylist': True}
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url)
        filename = ydl.prepare_filename(info)
        return filename

bot.run(bot_token)
