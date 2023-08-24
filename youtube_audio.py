import av  # python interface to ffmpeg (can stream audio from a url and decode the frames into raw audio samples)
from pytube import (
    YouTube,
)  # youtube API (can get the url of the audio stream of a youtube video)
import sounddevice as sd  # play audio samples (send them to the sound card)
import queue  # thread-safe queue, get() blocks when queue is empty, put() blocks when queue is full
import numpy as np
import threading


class StreamingAudioPlayer:
    """
    Keeps playing audio (in the background, in another thread) that you feed it.
    Feed it audio using `add_audio(data)` where `data` is a N by 2 numpy array
    of audio samples. Each of the 2 columns is a channel (left and right). The N
    rows are samples. The sample rate of `data` should be whatever was specified
    when constructing this class.

    Will start playing as soon as audio samples are added. Will stop playing
    when close() is called. close() also cleans up resources (audio resources to
    be specific). If you wanna play again after calling close(), you'll need to
    create a new StreamingAudioPlayer object.

    Example usage:
        player = StreamingAudioPlayer(sample_rate=44100)
        player.add_audio(np.random.rand(44100, 2))  # add 1 second of random audio samples
                                                    # starts playing immediately after
                                                    # the first call to add_audio()
        player.add_audio(np.random.rand(44100, 2))  # add another second of random audio samples
        # etc...
        player.close()  # stop playing and clean up resources (audio resources to be specific)
    """

    def __init__(self, sample_rate, queue_size=200):
        assert sample_rate > 0, "sample_rate must be greater than 0"
        assert queue_size > 0, "queue_size must be greater than 0"

        self._queue = queue.Queue(maxsize=queue_size)

        self._audio_stream = sd.OutputStream(
            samplerate=sample_rate, channels=2, callback=self._audio_callback
        )  # assumes stereo audio
        self._audio_stream.start()

        # important: modified by _audio_callback thread, do not modify from any other threads unless you add a mutex
        self._leftover_buffer = (
            None  # leftover audio frames from the previous call to _audio_callback
        )

    def add_audio(self, audio_data):
        """
        Add audio samples to the queue of samples to be played. If the queue is
        full, this function will block until there is space in the queue.
        """
        assert audio_data.shape[1] == 2, "audio_data must have 2 channels (columns)"

        self._queue.put(audio_data)

    def close(self):
        """
        Stop playing audio and clean up any resources.
        """
        self._audio_stream.stop()
        self._audio_stream.close()

    def _audio_callback(self, outdata, frames, time, status):
        """
        Executed by the audio stream (a thread of its own) whenever it needs more audio samples.
        Place new audio samples in outdata.
        """
        buffer = np.empty((0, 2))

        # add leftover audio samples from the previous call to _audio_callback
        if self._leftover_buffer is not None and len(self._leftover_buffer) > 0:
            buffer = np.vstack((buffer, self._leftover_buffer))
            self._leftover_buffer = None

        # fetch new audio samples from the queue
        try:
            audio_data = self._queue.get_nowait()
            buffer = np.vstack((buffer, audio_data))
        except queue.Empty:
            pass  # no new audio samples in the queue

        # fill outdata with buffer, and save leftover audio samples for the next call to _audio_callback
        if len(buffer) >= len(outdata):
            outdata[:] = buffer[: len(outdata)]
            self._leftover_buffer = buffer[len(outdata) :]
        else:
            outdata[: len(buffer)] = buffer
            outdata[len(buffer) :] = 0  # fill remaining with zeros


class YouTubeAudioPlayer:
    """
    Plays audio from a YouTube video. The audio is *streamed* from YouTube and played in the background.
    Both the streaming and the playing happen in the background (i.e. in a separate thread).

    Example usage:
        url = "https://www.youtube.com/watch?v=W-P_ShiZqvg" # Lucky I'm in love with my best friend, dah dah dah dah, dah dah, dah - great song
        player = YouTubeAudioPlayer(url)
        player.play() # play from the beginning
        player.play(50) # now, skip to the 50 second mark and play from there
        player.play(10) # now, skip to the 10 second mark and play from there
        player.stop() # stop playing
    """

    def __init__(self, url):
        self._CHUNK_SIZE = 1  # number of audio frames at a time to feed to the player

        yt = YouTube(url)
        # get the url of the *audio* portion of the video ("the audio stream"")
        audio_stream_url = (
            yt.streams.filter(only_audio=True, file_extension="mp4").first().url
        )  # TODO this line takes a long time for some reason

        # we gonna use ffmpeg to receive audio frames and decode them
        self._container = av.open(audio_stream_url)
        self._audio_stream = next(
            s for s in self._container.streams if s.type == "audio"
        )

        self._stream_thread = None

    def play(self, start_time_seconds=0):
        """
        Start playing the audio at `start_time_seconds` into the video.
        """

        # if already playing, stop (i.e. exit the thread that's playing)
        self.stop()

        # we gonna pass the decoded audio frames to this player to play
        self._player = StreamingAudioPlayer(self._audio_stream.sample_rate)

        self._exit_worker = False
        self._stream_thread = threading.Thread(
            target=self._stream_and_play, args=(start_time_seconds,)
        )
        self._stream_thread.daemon = True
        self._stream_thread.start()

    def stop(self):
        """
        Stop playing the audio.
        """

        if self._stream_thread is not None:
            self._exit_worker = True
            self._stream_thread.join()  # wait for thread to exit
            self._player.close()

    def _stream_and_play(self, start_time_seconds):
        """
        Stream audio starting from `start_time_seconds` into the video, and play it.
        Set `self._exit_worker` to True to exit the thread executing this function.
        """

        seek_point = int(start_time_seconds / self._audio_stream.time_base)
        self._container.seek(seek_point, stream=self._audio_stream)

        chunk = []  # bunch of audio frames
        for packet in self._container.demux(self._audio_stream):
            for frame in packet.decode():
                if self._exit_worker:
                    return
                audio_data = frame.to_ndarray()
                audio_data = audio_data.transpose()
                chunk.append(audio_data)

                if len(chunk) == self._CHUNK_SIZE:
                    audio_data_combined = np.concatenate(chunk)
                    self._player.add_audio(audio_data_combined)
                    chunk.clear()
