import wave
import argparse
import numpy

# convert audio byte_sequence into numpy array and merge channels if stereo
def extract_samples(byte_sequence, nchannels, samplewidth):
    sample_sequence = []
    sequence_length = int(len(byte_sequence)/(nchannels*samplewidth))

    sw = samplewidth

    for i in range(sequence_length):
        # read from bytestream as signed integer
        if nchannels == 2:
            left = int.from_bytes(byte_sequence[i*2*sw:i*2*sw + sw],
                                  byteorder="little", signed=True)
            right = int.from_bytes(byte_sequence[i*2*sw + sw:i*2*sw + 2*sw],
                                   byteorder="little", signed=True)
            sample_sequence.append(left+right)
        elif nchannels == 1:
            center = int.from_bytes(byte_sequence[i*sw:i*sw + sw],
                                  byteorder="little", signed=True)
            sample_sequence.append(center)
        else:
            assert False, "invalid number of channels: %i" % nchannels
     
    # convert to numpy array and normalize to 1
    sample_data = numpy.asarray(sample_sequence) / (2**(8*samplewidth - 1))
    
    return sample_data
 
def block_average(block, threshold):
    framesum = 0.0
    for frame in block:
        framesum += abs(frame)
    
    framesum = framesum/float(len(block))
    return framesum > threshold

def find_threshold_marker(wave_file, threshold, duration):
    marker = []
    start_marker = 0
    in_section = False
    cursor = 0
    eof = wave_file.getnframes() - 1

    nchannels = wave_file.getnchannels()
    samplewidth = wave_file.getsampwidth()

    while cursor < eof:
        byteseq = wave_file.readframes(duration)
        block = extract_samples(byteseq, nchannels, samplewidth)
        if not in_section and block_average(block, threshold):
            start_marker = cursor
            in_section = True
        elif in_section and not block_average(block, threshold):
            end_marker = cursor + duration
            marker.append((start_marker, end_marker))
            in_section = False
        cursor += duration

    if in_section:
        marker.append((start_marker, eof))
   
    return marker 
 
def open_wave(filename, input_wav):
    output_wav = wave.open(filename, "wb")
    output_wav.setnchannels(1)
    output_wav.setsampwidth(input_wav.getsampwidth())
    output_wav.setframerate(input_wav.getframerate())
    return output_wav

def main():
    parser = argparse.ArgumentParser(
        description='split a wave file in non null sections')
    parser.add_argument(
        'file', type=str,
        help='path to input file')
    parser.add_argument(
        'threshold', type=float,
        help='threshold for activation')
    parser.add_argument(
        'duration', type=float,
        help='minimal duration in seconds to accept break')
    args = parser.parse_args()

    wave_file = wave.open(args.file, "rb")
    nchannels = wave_file.getnchannels()
    assert nchannels is 1, "File needs to be mono"

    duration = int(args.duration * wave_file.getframerate())
    threshold = args.threshold
    print("threshold %s duration %s" % (threshold, duration))

    marker = find_threshold_marker(wave_file, threshold, duration) 

    print(marker)

    base_filename = args.file[:-4]
    for i, m in enumerate(marker):
        filename = base_filename + ("_%i" % i) + ".wav"
        out_wave = open_wave(filename, wave_file)
        wave_file.setpos(m[0])
        raw_data = wave_file.readframes(m[1]-m[0])
        out_wave.writeframes(raw_data)
        out_wave.close()
        

if __name__ == "__main__":
    main()

