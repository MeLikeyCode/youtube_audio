"""A small command line program to manually test the YouTubeAudioPlayer class. Run this file with no arguments and follow the prompt."""

from youtube_audio import YouTubeAudioPlayer

if __name__ == "__main__":
    url = "https://www.youtube.com/watch?v=W-P_ShiZqvg"
    player = YouTubeAudioPlayer(url)

    while True:
        seek_time_seconds = input("type a number (in seconds) to seek to that point in the audio; type exit to exit: ")
        
        if seek_time_seconds != "exit":
            player.play(float(seek_time_seconds))
        else:
            player.stop()
            break

