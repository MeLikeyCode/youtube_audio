# Python YouTube Audio Player
A small/simple python module that allows you to easily play the audio of a YouTube video.

# Usage
~~~~~~~~~~~~~~~~~~~~~~python
from youtube_audio import YouTubeAudioPlayer

url = "https://www.youtube.com/watch?v=W-P_ShiZqvg" # Lucky I'm in love with my best friend, dah dah dah dah, dah dah, dah

player = YouTubeAudioPlayer(url)
player.play() # play from the beginning (plays in the background)
player.play(50) # now, skip to the 50 second mark and play from there
player.play(10) # now, skip to the 10 second mark and play from there
player.stop() # stop playing (cleans up resources as well)
~~~~~~~~~~~~~~~~~~~~~~

Of course, you can create multiple instance of the player, etc etc.

# Installation
Just install the dependencies in your environment:
- av
- pytube
- numpy
- sounddevice

And then copy `youtube_audio.py` to your project.

Maybe in the future, if I'm not lazy, I'll make this a package haha.

**Enjoy!** (or not, I don't care)
