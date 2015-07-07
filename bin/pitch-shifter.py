#!python
import argparse
import matplotlib.pyplot as pp
import numpy as np
import scipy
import scipy.interpolate
import scipy.io.wavfile
import sys
import logging
import pitchshifter as ps

log = logging.getLogger("pitch.shifter")
logging.basicConfig(filename='example.log', filemode='w', level=logging.DEBUG)

def main(args={}):
    # Try to open the wav file and read it
    try:
        source = scipy.io.wavfile.read(args.source)
    except:
        print("File {0} does not exist".format(args.source))
        sys.exit(-1)

    RIGHT = 0
    LEFT  = 1
    HOP = int((1-args.overlap)*args.chunk_size)
    HOP_OUT = int(HOP*(2**(args.pitch/12.0)))

    audio_samples = source[1].tolist()
    rate = source[0]
    source_mono = np.asarray(
        [sample[RIGHT] for sample in audio_samples], 
        dtype=np.int16)

    res = ps.stft(source_mono, rate, args.chunk_size, HOP)

    # Fix this phase correction bit...
    adjusted = []
    last_phase = 0
    phaseCumulative = 0
    for i in range(len(res)):
        phase_frame = np.angle(res[i])
        
        deltaPhi = phase_frame - last_phase
        last_phase = phase_frame

        deltaPhiPrime = deltaPhi - HOP*2*np.pi*np.arange(len(res[i]))/len(res[i])

        deltaPhiPrimeMod = np.mod(deltaPhiPrime+np.pi, 2*np.pi) - np.pi

        trueFreq = (2*np.pi*np.arange(len(res[i])))/len(res[i]) + deltaPhiPrimeMod/HOP

        phaseCumulative = phaseCumulative + HOP_OUT * trueFreq;

        adjusted.append(ps.complex_polarToCartesian(np.abs(res[i]), phaseCumulative))
    
    merged_together = np.asarray(ps.istft(adjusted, rate, args.chunk_size, HOP_OUT), dtype=np.int16)

    if args.no_resample:
        final = merged_together
    else:
        resampling_factor = HOP_OUT*1.0/HOP
        resampler = scipy.interpolate.interp1d(np.arange(0,len(merged_together)), merged_together, kind='linear')
        final = resampler(np.linspace(0,len(merged_together)-HOP,len(source_mono)))
        final = final * args.blend + (1-args.blend)*source_mono

    if args.debug:
        pp.plot(final)
        pp.show()
    
    output = scipy.io.wavfile.write(args.out, rate, np.asarray(final, dtype=np.int16))
    

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description = "Shifts the pitch of an input .wav file")
    parser.add_argument('--source', '-s', help='source .wav file', required=True)
    parser.add_argument('--out', '-o', help='output .wav file', required=True)
    parser.add_argument('--pitch', '-p', help='pitch shift', default=0, type=int)
    parser.add_argument('--blend', '-b', help='blend', default=1, type=float)
    parser.add_argument('--chunk-size', '-c', help='chunk size', default=512, type=int)
    parser.add_argument('--overlap', '-e', help='overlap', default=.5, type=float)
    parser.add_argument('--debug', '-d', help='debug flag', action="store_true")
    parser.add_argument('--no-resample', help='debug flag', action="store_true")  

    args = parser.parse_args()
    
    print(args)
    main(args)