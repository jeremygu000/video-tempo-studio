from moviepy.editor import VideoFileClip, AudioFileClip
import librosa
import soundfile as sf
import os
import shutil
import numpy as np


# declare constants
video_output_file_temp = 'output_video_temp.mp4'
audio_output_file_temp = "output_audio_temp.mp3"
audio_output_file       = "output_audio.wav"

#from audiotsm import wsola
#from audiotsm.io.wav import WavReader, WavWriter
def separate_video_audio(input_file, slow_factor, audio_output_file):
    video = VideoFileClip(input_file)
   
    # Extracting audio
    audio_clip = video.audio
    audio_clip.write_audiofile(audio_output_file_temp)

    # Slow down audio
    stretch_audio(audio_output_file_temp, audio_output_file, slow_factor)

    # Remove audio and Slow down video
    video = video.set_audio(None)
    video_clip = video.speedx(slow_factor)
   
    # Save video
    video_clip.write_videofile(video_output_file_temp, codec='libx264')


    # Close the clips
    video_clip.close()
    audio_clip.close()

#def stretch_audio(input_file, output_file, speed):
#    with WavReader(input_file) as reader:
#        with WavWriter(output_file, reader.channels, reader.samplerate) as writer:
#            tsm = wsola(reader.channels, speed)
#            tsm.run(reader, writer)
def stretch_audio(audio_file, output_file, slowdown_factor):
    print("start to stretch audio")
    # Load the audio clip using librosa
    y, sr = librosa.load(audio_file, sr=None, mono=False)
    
    # Slow down the audio using Librosa

    # Below one use rubberband
    # y_slow = librosa.effects.time_stretch(y, rate=slowdown_factor)

    # Below one use phase_vocoder
    D       = librosa.stft(y, n_fft=2048, hop_length=512)
    D_slow  = librosa.phase_vocoder(D, rate=slowdown_factor, hop_length=512)
    y_slow  = librosa.istft(D_slow, hop_length=512)

    # Normalize audio 

    # Using RMS
    #rms = np.sqrt(np.mean(np.square(y_slow)))
    # Set the desired RMS energy for normalization (e.g., -10 dB)
    #target_rms = 10 ** (-1 / 1)
    # Compute the scaling factor
    #scale = target_rms / rms
    # Apply normalization
    #normalized_audio = y_slow * scale
    # sf.write(output_file, normalized_audio.T, sr)

    # Use max absolute amplitude
    max_amplitude = np.max(np.abs(y_slow))

    # Normalize the audio by dividing by the maximum amplitude
    y_normalized = y_slow / max_amplitude
    
    # Save the modified audio to a file
    sf.write(output_file, y_normalized.T, sr)
    print("stretch audio finished")


def combine_video_audio(video_file, audio_file, output_file):
    # Load video and audio clips
    video_clip = VideoFileClip(video_file)
    audio_clip = AudioFileClip(audio_file)
    
    # Set the audio of the video clip to the loaded audio clip
    video_clip = video_clip.set_audio(audio_clip)
    
    # Write the combined clip to a file
    video_clip.write_videofile(output_file, codec='libx264', audio_codec='aac')
    
    # Close the clips
    video_clip.close()
    audio_clip.close()

def get_recent_video_files(directory, num_files):
    video_extensions = ['.mp4', '.avi', '.mov', '.mkv', 'mpg']  # Add more extensions if needed
    # Get a list of all files in the directory
    all_files = os.listdir(directory)
    # Filter out directories and non-video files
    video_files = [os.path.join(directory, file) for file in all_files
                   if os.path.isfile(os.path.join(directory, file))
                   and os.path.splitext(file)[1].lower() in video_extensions]
    # Sort video files based on modification time
    recent_video_files = sorted(video_files, key=os.path.getmtime, reverse=True)
    # Return the specified number of recent video files
    return recent_video_files[:num_files]


def remove_extension(filename):
    return os.path.splitext(filename)[0]


# Create a subfolder
def create_subfolder(directory, subfolder_name):
    subfolder_path = os.path.join(directory, subfolder_name)
    if not os.path.exists(subfolder_path):
        os.mkdir(subfolder_path)
        print(f"Subfolder '{subfolder_name}' created successfully.")
    else:
        print(f"Subfolder '{subfolder_name}' already exists.")

# Main process
def processvideo(input_file):
    print(input_file)

    videofilename_without_extension = remove_extension(input_file)

    # Create subfolder 'BianSu'
    subfolder_name = videofilename_without_extension + '_BianSu'
    create_subfolder(directory, subfolder_name)

    # Process 60%
    slow_factor = 0.6  # Change this factor to adjust the speed
    video_output_file = videofilename_without_extension + '_60.mp4'

    separate_video_audio(input_file, slow_factor, audio_output_file)
    combine_video_audio(video_output_file_temp, audio_output_file, video_output_file)
    if os.path.exists(video_output_file_temp): 
        os.remove(video_output_file_temp)
    if os.path.exists(audio_output_file_temp): 
        os.remove(audio_output_file_temp)
    if os.path.exists(audio_output_file): 
        os.remove(audio_output_file)

    # Move the output file to BianSu folder
    new_videofile_file = os.path.join(directory, subfolder_name, video_output_file)
    shutil.move(video_output_file, new_videofile_file)

    # Process 70%
    slow_factor = 0.7  # Change this factor to adjust the speed
    video_output_file = videofilename_without_extension + '_70.mp4'

    separate_video_audio(input_file, slow_factor, audio_output_file)
    combine_video_audio(video_output_file_temp, audio_output_file, video_output_file)
    if os.path.exists(video_output_file_temp): 
        os.remove(video_output_file_temp)
    if os.path.exists(audio_output_file_temp): 
        os.remove(audio_output_file_temp)
    if os.path.exists(audio_output_file): 
        os.remove(audio_output_file)

    # Move the output file to BianSu folder
    new_videofile_file = os.path.join(directory, subfolder_name, video_output_file)
    shutil.move(video_output_file, new_videofile_file)

    # Process 80%
    slow_factor = 0.8  # Change this factor to adjust the speed
    video_output_file = videofilename_without_extension + '_80.mp4'

    separate_video_audio(input_file, slow_factor, audio_output_file)
    combine_video_audio(video_output_file_temp, audio_output_file, video_output_file)
    if os.path.exists(video_output_file_temp): 
        os.remove(video_output_file_temp)
    if os.path.exists(audio_output_file_temp): 
        os.remove(audio_output_file_temp)
    if os.path.exists(audio_output_file): 
        os.remove(audio_output_file)

    # Move the output file to BianSu folder
    new_videofile_file = os.path.join(directory, subfolder_name, video_output_file)
    shutil.move(video_output_file, new_videofile_file)

    # Process 90%
    slow_factor = 0.9  # Change this factor to adjust the speed
    video_output_file = videofilename_without_extension + '_90.mp4'

    separate_video_audio(input_file, slow_factor, audio_output_file)
    combine_video_audio(video_output_file_temp, audio_output_file, video_output_file)
    if os.path.exists(video_output_file_temp): 
        os.remove(video_output_file_temp)
    if os.path.exists(audio_output_file_temp): 
        os.remove(audio_output_file_temp)
    if os.path.exists(audio_output_file): 
        os.remove(audio_output_file)

    # Move the output file to BianSu folder
    new_videofile_file = os.path.join(directory, subfolder_name, video_output_file)
    shutil.move(video_output_file, new_videofile_file)

    # Move the input file to BianSu folder
    new_inputvideofile_file = os.path.join(directory, subfolder_name, input_file)
    shutil.move(input_file, new_inputvideofile_file)

directory = './'
num_files = 100  # Change this to the number of recent video files you want to retrieve
recent_video_files = get_recent_video_files(directory, num_files)
for inputfile in recent_video_files:
    processvideo(inputfile)
