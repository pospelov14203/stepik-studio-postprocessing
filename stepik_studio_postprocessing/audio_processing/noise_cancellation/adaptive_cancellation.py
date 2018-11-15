# Original code:
# https://github.com/loehnertz/rattlesnake

import logging
import wave

import numpy as np

# Sample width of the live recording
from stepik_studio_postprocessing.utils.descriptors.audio_file_descriptor import AudioFileDescriptor
from stepik_studio_postprocessing.utils.types.audio_suffixes import AudioSuffixes

logger = logging.getLogger(__name__)


class AdaptiveNoiseCanceller(object):
    def __init__(self, output_framerate = None,
                 channels = None,
                 sample_width = None,
                 ratio: float = 1.0,
                 chunk_size: int = 1):
        self.output_framerate = output_framerate
        self.channels = channels
        self.sample_width = sample_width
        self.ratio = ratio
        self.chunk_size = chunk_size

    def process(self, main_audio, aux_audio, output_file: str):
        """
        Mixes main audio file with inverted auxiliary audio file to cancel background noise.
        :param main_audio: AudioFileDescriptor of main audio
        :param aux_audio: AudioFileDescriptor of auxiliary audio
        :param output_file: Path to output file
        :return: AudioFileDescriptor of result file
        """
        if main_audio.audio_type is not AudioSuffixes.WAV:
            logger.error('Wrong type of audio file')
            raise TypeError('Type of main audio file should be {} instead of {}'
                            .format(AudioSuffixes.WAV, main_audio.audio_type))

        if aux_audio.audio_type is not AudioSuffixes.WAV:
            logger.error('Wrong type of audio file')
            raise TypeError('Type of auxiliary audio file should be {} instead of {}'
                            .format(AudioSuffixes.WAV, aux_audio.audio_type))

        main_wf = wave.open(main_audio.path, 'r')
        aux_wf = wave.open(aux_audio.path, 'r')

        if not self.output_framerate:
            self.output_framerate = main_wf.getframerate()

        if not self.sample_width:
            self.sample_width = main_wf.getsampwidth()

        if not self.channels:
            self.channels = main_wf.getnchannels()

        output_wf = self._get_output_waveform(output_file)

        original = main_wf.readframes(self.chunk_size)
        aux = aux_wf.readframes(self.chunk_size)

        while original != b'' and aux != b'':
            inverted_aux = self._invert(aux)
            mix = self._mix_samples(original, inverted_aux)
            output_wf.writeframes(b''.join(mix))

            original = main_wf.readframes(self.chunk_size)
            aux = aux_wf.readframes(self.chunk_size)

        output_wf.close()
        main_wf.close()
        aux_wf.close()

        return AudioFileDescriptor(output_file)

    def _check_compatibility(self, main_wf, aux_wf):
        """
        Checks framerate compability of input files. It must be the same.
        :param main_wf: Waveform of main audio file
        :param aux_wf: Waveform of auxiliary audio file
        """
        if main_wf.getframerate() != aux_wf.getframerate():
            logger.error('Input audio files must have the same framerate')
            raise ValueError('Input audio files must have the same framerate')

        if main_wf.getsampwidth() != aux_wf.getsampwidth():
            logger.warning('Input audio files have difference sample width. '
                           'This can lead to loss of quality.')

    def _get_output_waveform(self, output_path: str):
        """
        Opens waveform for writing the result

        :param output_path: path to output file
        :return: Wave_write
        """

        wf = wave.open(output_path, 'wb')
        wf.setnchannels(self.channels)
        wf.setsampwidth(self.sample_width)
        wf.setframerate(self.output_framerate)
        return wf

    def _invert(self, data):
        """
        Inverts the byte data it received utilizing an XOR operation.

        :param data: A chunk of byte data
        :return inverted: The same size of chunked data inverted bitwise
        """

        # Convert the bytestring into an integer
        intwave = np.fromstring(data, np.int32)
        # Invert the integer
        intwave = np.invert(intwave)
        # Convert the integer back into a bytestring
        inverted = np.frombuffer(intwave, np.byte)
        # Return the inverted audio data
        return inverted

    def _mix_samples(self, sample_1, sample_2):
        """
        Mixes two samples into each other

        :param sample_1: A bytestring containing the first audio source
        :param sample_2: A bytestring containing the second audio source
        :param ratio: A float which determines the mix-ratio of the two samples (the higher, the louder the first sample)
        :return mix: A bytestring containing the two samples mixed together
        """

        # Calculate the actual ratios based on the float the function received
        (ratio_1, ratio_2) = self._get_ratios()
        # Convert the two samples to integers
        intwave_sample_1 = np.fromstring(sample_1, np.int16)
        intwave_sample_2 = np.fromstring(sample_2, np.int16)
        # Mix the two samples together based on the calculated ratios
        intwave_mix = (intwave_sample_1 * ratio_1 + intwave_sample_2 * ratio_2).astype(np.int16)
        # Convert the new mix back to a playable bytestring
        mix = np.frombuffer(intwave_mix, np.byte)
        return mix

    def _get_ratios(self):
        """
        Calculates the ratios using a received float

        :param ratio: A float betwenn 0 and 2 resembling the ratio between two things
        :return ratio_1, ratio_2: The two calculated actual ratios
        """

        ratio = float(self.ratio)
        ratio_1 = ratio / 2
        ratio_2 = (2 - ratio) / 2
        return ratio_1, ratio_2
