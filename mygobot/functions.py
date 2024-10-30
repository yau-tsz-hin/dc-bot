import yt_dlp
import os
import glob
import asyncio
import discord
from discord.utils import get
from discord.ext.commands import Bot

class Player:
    def __init__(self, ctx: discord.Interaction, url: str, bot: Bot, loop=False) -> None:
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
