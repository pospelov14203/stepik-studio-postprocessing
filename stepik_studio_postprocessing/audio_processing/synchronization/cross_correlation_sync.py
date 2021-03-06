import logging
import wave

import numpy as np
from scipy.signal import correlate

from stepik_studio_postprocessing.utils import normalize_signal, frames_to_seconds, get_output_waveform, AudioSuffixes

logger = logging.getLogger(__name__)


class CorrelationSynchronizer(object):
    def __init__(self, chunksize: int = 10000):
        self.chunksize = chunksize

    def process(self, audio_1, audio_2, output_file: str):
        self._check_compability(audio_1, audio_2)

        diff = self.get_frames_diff(audio_1, audio_2)

        if diff <= 0:
            source = wave.open(audio_1.path, 'r')
        else:
            source = wave.open(audio_2.path, 'r')

        output = get_output_waveform(output_file,
                                     source.getnchannels(),
                                     source.getsampwidth(),
                                     source.getframerate())

        original = source.readframes(self.chunksize)
        silence = np.zeros(abs(diff), audio_1.get_sample_size())
        silence = np.frombuffer(silence, np.byte)

        output.writeframes(b''.join(silence))

        while original != b'':
            output.writeframes(b''.join(np.frombuffer(original, np.byte)))
            original = source.readframes(self.chunksize)

        source.close()
        output.close()

    def get_seconds_diff(self, audio_1, audio_2) -> float:
        self._check_compability(audio_1, audio_2)

        return frames_to_seconds(self.get_frames_diff(audio_1, audio_2),
                                 audio_1.get_framerate())

    def get_frames_diff(self, audio_1, audio_2) -> int:
        self._check_compability(audio_1, audio_2)

        wf_1 = wave.open(audio_1.path, 'r')
        wf_2 = wave.open(audio_2.path, 'r')

        frames_1 = wf_1.readframes(self.chunksize)
        frames_2 = wf_2.readframes(self.chunksize)

        string_size = audio_1.get_sample_size()

        frames_1 = np.fromstring(frames_1, string_size)
        frames_2 = np.fromstring(frames_2, string_size)

        frames_1 = normalize_signal(frames_1)
        frames_2 = normalize_signal(frames_2)

        corr = correlate(frames_1, frames_2)
        lag = np.argmax(corr)

        wf_1.close()
        wf_2.close()

        return lag - frames_2.size

    def _check_compability(self, audio_1, audio_2):
        if audio_1.audio_type != AudioSuffixes.WAV or \
                audio_2.audio_type != AudioSuffixes.WAV:
            logger.error('Only {} files supported'.format(AudioSuffixes.WAV))
            raise TypeError('Only {} files supported'.format(AudioSuffixes.WAV))

        if audio_1.get_n_channels() != audio_2.get_n_channels():
            logger.error('Audio files must be with the same number of channels')
            raise TypeError('Audio files must be with the same number of channels')

        if audio_1.get_framerate() != audio_2.get_framerate():
            logger.error('Audio files must be with the same framerate')
            raise TypeError('Audio files must be with the same framerate')

        if audio_1.get_sample_width() != audio_2.get_sample_width():
            logger.error('Audio files must be with the same framerate')
            raise TypeError('Audio files must be with the same framerate')
