import math
import random

from . import SAMPLE_RATE
from .signal import Signal

__all__ = ('Sample', 'SineWave', 'SquareWave', 'SawtoothWave', 'TriangleWave', 'Noise', 'BrownNoise', 'Digitar', 'harmonics')

class Sample(Signal):
    """
    An infinitely long sound generated by a simple algorithm
    """
    def __init__(self, frequency):
        self.frequency = float(frequency)
        self.duration = float('inf')

    @property
    def period(self):
        return 1/self.frequency * SAMPLE_RATE

class SineWave(Sample):
    """
    A sample that outputs a sine wave at the given frequency
    """
    def amplitude(self, frame):
        return math.sin(frame * 2 * math.pi / self.period)

class SquareWave(Sample):
    """
    A sample that outputs a square wave at the given frequency

    Due to aliasing, you may want to use a series of sine wave harmonics if you want to
    obtain a more pleasant sound.
    """
    def __init__(self, frequency, split=0.5):
        super(SquareWave, self).__init__(frequency)
        self.split = split

    def amplitude(self, frame):
        return 1 if frame % self.period < self.period*self.split else -1

class SawtoothWave(Sample):
    """
    A sample that outputs a sawtooth wave at the given frequency

    Due to aliasing, you may want to use a series of sine wave harmonics if you want to
    obtain a more pleasant sound.
    """
    def amplitude(self, frame):
        return frame % self.period / self.period * 2 - 1

class TriangleWave(Sample):
    """
    A sample that outputs a triangle wave at the given frequency

    Due to aliasing, you may want to use a series of sine wave harmonics if you want to
    obtain a more pleasant sound.
    """
    def amplitude(self, frame):
        pframe = frame % self.period
        hperiod = self.period/2
        qperiod = hperiod/2
        if pframe < qperiod:
            return pframe / qperiod
        pframe -= qperiod
        if pframe < hperiod:
            return pframe / -hperiod*2 + 1
        pframe -= hperiod
        return pframe / qperiod - 1

class Noise(Sample):
    """
    A sample that outputs white noise, random data uniformly distributed over [0,1].
    """
    # I... guess this is technically pure?
    def __init__(self):
        super(Noise, self).__init__(0)

    def amplitude(self, frame):
        return random.random() * 2 - 1

class BrownNoise(Sample):
    """
    A sample that outputs brown noise, the integration of white noise.

    It is technically pure, but output may more closely resemble white noise if sample impurely.
    """
    def __init__(self, fac=0.5):
        super(BrownNoise, self).__init__(0)
        self.prev = 0.
        self.fac = float(fac)

    def amplitude(self, frame):
        self.prev += (random.random() * 2 - 1) * self.fac
        if self.prev > 1: self.prev = 1.
        elif self.prev < -1: self.prev = -1.
        return self.prev


class Digitar(Sample):
    """
    A sample that implements the Karplus-Strong plucked string synthesis algorithm.
    The basic idea is that an wavetable initially populated with random noise run though
    a low-pass filter cyclically, gradually removing inharmonic components and smoothing
    the waveform. The sound is tuned by keeping a separate "phase" counter which causes the
    output to cycle through the wavetable at a different speed than the filter, effectively
    adjusting the period of the signal. The decay rate is adjusted by changing the size of
    the wavetable - the smaller the wavetable, the faster the filter adjusts the signal and
    the faster that the sound decays. Keep in mind that if it decays very quickly, then
    the noise doesn't have time to resolve into a tone, and the output will sound more
    drum-like.

    :param frequency:       The desired output frequency
    :param buffersize:      The size of the wavetable.
                            Optional, defaults to a good plucked string sound.
    :param wavesrc:         A signal to sample to produce the initial wavetable.
                            Optional, defaults to white noise.
    """
    def __init__(self, frequency, buffersize=256, wavesrc=None):
        self.wavesrc = wavesrc if wavesrc is not None else Noise()
        super(Digitar, self).__init__(frequency)
        self.buffersize = buffersize
        self.sample_window = None
        self.cur_frame = None
        basefreq = SAMPLE_RATE * 1./self.buffersize
        self.phaseinc = frequency / basefreq
        self.phase = 0
        self.new_buffer()
        self.pure = False

    def new_buffer(self):
        self.sample_window = [self.wavesrc.amplitude(i) for i in range(self.buffersize)]
        self.cur_frame = 0
        self.phase = 0

    def get_buffer(self, frame):
        return self.sample_window[frame % self.buffersize]

    def set_buffer(self, frame, value):
        self.sample_window[frame % self.buffersize] = value

    def tick(self):
        self.set_buffer(self.cur_frame + 1, self.get_buffer(self.cur_frame) * 0.3 + self.get_buffer(self.cur_frame + 1) * 0.7)
        self.cur_frame += 1
        self.phase = (self.phase + self.phaseinc) % self.buffersize

    def seek(self, frame):
        if frame < self.cur_frame:
            self.cur_frame = 0
        while self.cur_frame < frame:
            self.tick()

    def amplitude(self, frame):
        self.seek(frame)
        s1 = self.get_buffer(int(self.phase))
        s2 = self.get_buffer(int(self.phase) + 1)
        interp = self.phase - int(self.phase)
        return interp * s2 + (1-interp) * s1

def harmonics(freq, ns=(1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16), subsample=SineWave):
    """
    Generate a number of harmonics of a given sample. The base tone is treated as the first harmonic.

    :param freq:        The base frequency to use
    :param ns:          A list of the harmonics to produce.
                        Optional, defauts to the first 16 harmonics.
    :param subsample:   The class of the sample to use.
                        Optional, defaults to a sine wave.
    """
    return [subsample(freq*n) for n in ns]
