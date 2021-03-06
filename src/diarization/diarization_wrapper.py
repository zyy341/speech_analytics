import configparser
import os
from pathlib import Path

import numpy as np
from pydiarization.diarization_wrapper import rttm_to_string
from scipy.io import wavfile

from src.utils import clear_dir
from .pyBK.main import runDiarization


# helper function
def getCurrentSpeakerCut(rttmString):
    return float(rttmString.split(' ')[3]), float(rttmString.split(' ')[3]) + float(rttmString.split(' ')[4]), \
           rttmString.split(' ')[7]


def runDiarization_wrapper(showName, signal, sr, diarization_dir: Path):
    """Running Diarization from pyBK and returning stereo array in output"""

    # reading pyBK config file
    configFile = diarization_dir / 'pyBK' / 'config.ini'
    config = configparser.ConfigParser()
    config.read(configFile)

    # extracting file name
    baseFileName = os.path.basename(showName)
    fileName = os.path.splitext(baseFileName)[0]

    # fix paths
    for k in config['PATH']:
        config['PATH'][k] = str(diarization_dir / config['PATH'][k]) + '/'

    # If the output file already exists from a previous call it is deleted
    if os.path.isfile(config['PATH']['output'] + config['EXPERIMENT']['name'] + config['EXTENSION']['output']):
        os.remove(config['PATH']['output'] + config['EXPERIMENT']['name'] + config['EXTENSION']['output'])

    if os.path.isfile(config['PATH']['file_output'] + config['EXPERIMENT']['name'] + config['EXTENSION']['audio']):
        os.remove(config['PATH']['file_output'] + config['EXPERIMENT']['name'] + config['EXTENSION']['audio'])

    # Output folder is created
    if not os.path.isdir(config['PATH']['output']):
        os.mkdir(config['PATH']['output'])

    # Output folder for wav file is created
    if not os.path.isdir(config['PATH']['file_output']):
        os.mkdir(config['PATH']['file_output'])

    # Start of diarization
    print('\nProcessing file', fileName)
    runDiarization(fileName, signal, sr, config)

    # Parsing rttm file for extraction speakers time
    rttm_file = config['EXPERIMENT']['name'] + ".rttm"
    path = config['PATH']['output'] + rttm_file
    rttmString = rttm_to_string(path)
    resArray = rttmString.split('SPEAKER')

    # Reading mono file
    signal = (signal * 2 ** 16 - 1) / 2
    signal = signal.astype(np.int16)

    # arrays for left and right  channels of stereo file
    left = np.zeros(len(signal))
    right = np.zeros(len(signal))

    # extracting speech of every speaker#1  and speaker#2
    for i in range(1, len(resArray)):
        # convertion time to sample number
        begin, end, speaker = getCurrentSpeakerCut(resArray[i])
        begin = int(begin * sr)
        end = int(end * sr)

        if speaker == 'speaker1':
            left[begin:end] = signal[begin:end]
        elif speaker == "speaker2":
            right[begin:end] = signal[begin:end]
        else:
            left[begin:end] = signal[begin:end]
            right[begin:end] = signal[begin:end]

    # convert float to int - it help to avoid problems with incorrectly saved wav file
    # combine left and right signal into one 2D array
    left = left.astype(np.int16)
    right = right.astype(np.int16)
    stereo_array = np.vstack((left, right)).T

    # saving stereo file
    output_file = config['PATH']['file_output'] + fileName + "_stereo.wav"
    wavfile.write(output_file, sr, stereo_array)

    # cleanup
    clear_dir(diarization_dir / 'pyBK' / 'out')
    clear_dir(diarization_dir / 'pyBK' / 'sad')

    return output_file, left, right, stereo_array
