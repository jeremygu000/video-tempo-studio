from moviepy.editor import VideoFileClip, AudioFileClip
import librosa
import soundfile as sf
import os
import shutil
import numpy as np
from pathlib import Path
import argparse
import sys
import time
import json
import subprocess


# declare constants
VIDEO_DIRECTORY = os.environ.get("VIDEO_SOURCE_DIR", str(Path.home() / "Videos"))
SPEED_FACTORS = [0.6, 0.7, 0.8, 0.9]
NUM_FILES = 100
FILE_READY_CHECKS = 3
FILE_READY_INTERVAL_SECONDS = 20
FFPROBE_TIMEOUT_SECONDS = 20
VIDEO_EXTENSIONS = [
    ".mp4",
    ".m4v",
    ".avi",
    ".mov",
    ".mkv",
    ".mpg",
    ".mpeg",
    ".webm",
    ".wmv",
    ".flv",
    ".ts",
    ".m2ts",
    ".mts",
    ".3gp",
]

#from audiotsm import wsola
#from audiotsm.io.wav import WavReader, WavWriter
def separate_video_audio(
    input_file,
    slow_factor,
    audio_output_file,
    audio_output_file_temp,
    video_output_file_temp,
    progress_callback=None,
):
    video = VideoFileClip(input_file)
    audio_clip = None
    video_clip = None
    try:
        # Extracting audio
        if callable(progress_callback):
            progress_callback("extract-audio")
        audio_clip = video.audio
        audio_clip.write_audiofile(audio_output_file_temp)

        # Slow down audio
        if callable(progress_callback):
            progress_callback("stretch-audio")
        stretch_audio(audio_output_file_temp, audio_output_file, slow_factor)

        # Remove audio and Slow down video
        if callable(progress_callback):
            progress_callback("render-video")
        muted_video = video.set_audio(None)
        video_clip = muted_video.speedx(slow_factor)

        # Save video
        video_clip.write_videofile(video_output_file_temp, codec='libx264')
    finally:
        if video_clip is not None:
            video_clip.close()
        if audio_clip is not None:
            audio_clip.close()
        video.close()

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

    # Normalize the audio by dividing by the maximum amplitude.
    # Guard against silent audio to avoid division by zero (NaN/Inf).
    if max_amplitude > 0:
        y_normalized = y_slow / max_amplitude
    else:
        y_normalized = y_slow
    
    # Save the modified audio to a file
    sf.write(output_file, y_normalized.T, sr)
    print("stretch audio finished")


def combine_video_audio(video_file, audio_file, output_file):
    # Load video and audio clips
    video_clip = VideoFileClip(video_file)
    audio_clip = AudioFileClip(audio_file)
    output_clip = None
    try:
        # Set the audio of the video clip to the loaded audio clip
        output_clip = video_clip.set_audio(audio_clip)

        # Write the combined clip to a file
        output_clip.write_videofile(output_file, codec='libx264', audio_codec='aac')
    finally:
        if output_clip is not None:
            output_clip.close()
        audio_clip.close()
        video_clip.close()


def emit_progress(percent, message):
    pct = max(0, min(100, int(percent)))
    print(f"PROGRESS {pct} {message}", flush=True)


def emit_skip_reason(reason):
    print(f"SKIP_REASON {reason}", flush=True)

def get_recent_video_files(directory, num_files):
    generated_suffixes = ("_60", "_70", "_80", "_90")
    # Get a list of all files in the directory
    all_files = os.listdir(directory)
    # Filter out directories and non-video files
    video_files = [os.path.join(directory, file) for file in all_files
                   if os.path.isfile(os.path.join(directory, file))
                   and os.path.splitext(file)[1].lower() in VIDEO_EXTENSIONS
                   and not os.path.splitext(file)[0].endswith(generated_suffixes)]
    # Sort video files based on modification time
    recent_video_files = sorted(video_files, key=os.path.getmtime, reverse=True)
    # Return the specified number of recent video files
    return recent_video_files[:num_files]


def resolve_ffprobe_bin():
    env_bin = os.environ.get("FFPROBE_BIN", "").strip()
    if env_bin:
        return env_bin

    detected = shutil.which("ffprobe")
    if detected:
        return detected

    # Common Homebrew locations on macOS.
    for fallback in ("/opt/homebrew/bin/ffprobe", "/usr/local/bin/ffprobe"):
        if os.path.exists(fallback):
            return fallback

    return "ffprobe"


def probe_media_file(file_path):
    command = [
        resolve_ffprobe_bin(),
        "-v",
        "error",
        "-show_streams",
        "-of",
        "json",
        file_path,
    ]
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=FFPROBE_TIMEOUT_SECONDS,
            check=False,
        )
    except FileNotFoundError:
        return (False, "ffprobe not found")
    except subprocess.TimeoutExpired:
        return (False, "ffprobe timeout")
    except Exception as exc:
        return (False, f"ffprobe error: {type(exc).__name__}: {exc}")

    if result.returncode != 0:
        detail = (result.stderr or "").strip() or f"exit code {result.returncode}"
        return (False, f"ffprobe failed: {detail}")

    try:
        payload = json.loads(result.stdout or "{}")
    except json.JSONDecodeError:
        return (False, "ffprobe output is not valid json")

    streams = payload.get("streams") or []
    has_video = any(stream.get("codec_type") == "video" for stream in streams)
    has_audio = any(stream.get("codec_type") == "audio" for stream in streams)
    if not has_video:
        return (False, "missing video stream")
    if not has_audio:
        return (False, "missing audio stream")
    return (True, None)


def is_file_ready(file_path, checks=2, interval_seconds=10):
    if not os.path.exists(file_path):
        return False

    previous_state = None
    for check_index in range(checks):
        try:
            current_state = (os.path.getsize(file_path), os.path.getmtime(file_path))
        except OSError:
            return False

        if previous_state is not None and current_state != previous_state:
            return False

        previous_state = current_state
        if check_index < checks - 1:
            time.sleep(interval_seconds)

    clip = None
    try:
        clip = VideoFileClip(file_path)
        duration = getattr(clip, "duration", None)
        return duration is not None and duration > 0
    except Exception:
        return False
    finally:
        if clip is not None:
            clip.close()


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

    input_path = Path(input_file)
    input_filename = input_path.name
    videofilename_without_extension = Path(input_filename).stem

    # Create subfolder 'BianSu'
    subfolder_name = videofilename_without_extension + '_BianSu'
    subfolder_path = Path(directory) / subfolder_name
    if subfolder_path.is_dir():
        shutil.rmtree(subfolder_path)
        print(f"Subfolder '{subfolder_name}' already exists and was reset.")
    create_subfolder(directory, subfolder_name)
    emit_progress(2, f"Preparing {input_filename}")

    total_speeds = len(SPEED_FACTORS)
    for index, slow_factor in enumerate(SPEED_FACTORS, start=1):
        speed_label = int(slow_factor * 100)
        base_pct = int(((index - 1) / total_speeds) * 90)
        emit_progress(base_pct + 5, f"{speed_label}%: separating audio/video")
        video_output_file = f"{videofilename_without_extension}_{speed_label}.mp4"
        temp_prefix = f"temp_{videofilename_without_extension}_{speed_label}"
        video_output_file_temp = f"{temp_prefix}_video.mp4"
        audio_output_file_temp = f"{temp_prefix}_audio.mp3"
        audio_output_file = f"{temp_prefix}_stretched.wav"
        stage_progress = {
            "extract-audio": base_pct + 8,
            "stretch-audio": base_pct + 12,
            "render-video": base_pct + 16,
        }

        def progress_callback(stage_name):
            stage_pct = stage_progress.get(stage_name)
            if stage_pct is not None:
                emit_progress(stage_pct, f"{speed_label}%: {stage_name}")

        try:
            separate_video_audio(
                input_file,
                slow_factor,
                audio_output_file,
                audio_output_file_temp,
                video_output_file_temp,
                progress_callback=progress_callback,
            )
            emit_progress(base_pct + 20, f"{speed_label}%: combining output")
            combine_video_audio(video_output_file_temp, audio_output_file, video_output_file)

            # Move the output file to BianSu folder
            new_videofile_file = os.path.join(directory, subfolder_name, video_output_file)
            shutil.move(video_output_file, new_videofile_file)
            emit_progress(base_pct + 25, f"{speed_label}%: output ready")
        finally:
            for temp_file in [video_output_file_temp, audio_output_file_temp, audio_output_file]:
                if os.path.exists(temp_file):
                    os.remove(temp_file)

    # Move the input file to BianSu folder
    emit_progress(95, "Moving source file")
    new_inputvideofile_file = os.path.join(directory, subfolder_name, input_filename)
    shutil.move(input_file, new_inputvideofile_file)
    emit_progress(100, "Completed")

directory = './'


def main(argv=None):
    global directory
    parser = argparse.ArgumentParser(description="Generate slowed-down video practice files.")
    parser.add_argument(
        "--directory",
        default=VIDEO_DIRECTORY,
        help="Directory containing source videos to process.",
    )
    parser.add_argument(
        "--file",
        default=None,
        help="Process a specific video file path. If provided, only this file is processed.",
    )
    args = parser.parse_args(argv if argv is not None else [])

    os.chdir(args.directory)
    directory = './'
    if args.file:
        inputfile = args.file
        if not is_file_ready(
            inputfile,
            checks=FILE_READY_CHECKS,
            interval_seconds=FILE_READY_INTERVAL_SECONDS,
        ):
            emit_skip_reason("not-ready file")
            print(f"Skip not-ready file: {inputfile}")
            return
        is_compatible, probe_reason = probe_media_file(inputfile)
        if not is_compatible:
            emit_skip_reason(probe_reason or "incompatible media")
            print(f"Skip incompatible file: {inputfile} ({probe_reason})")
            return
        try:
            processvideo(inputfile)
        except Exception as exc:
            print(f"Failed processing {inputfile}: {exc}")
        return

    recent_video_files = get_recent_video_files(directory, NUM_FILES)
    for inputfile in recent_video_files:
        if not is_file_ready(
            inputfile,
            checks=FILE_READY_CHECKS,
            interval_seconds=FILE_READY_INTERVAL_SECONDS,
        ):
            emit_skip_reason("not-ready file")
            print(f"Skip not-ready file: {inputfile}")
            continue
        is_compatible, probe_reason = probe_media_file(inputfile)
        if not is_compatible:
            emit_skip_reason(probe_reason or "incompatible media")
            print(f"Skip incompatible file: {inputfile} ({probe_reason})")
            continue
        try:
            processvideo(inputfile)
        except Exception as exc:
            print(f"Failed processing {inputfile}: {exc}")


if __name__ == "__main__":
    main(sys.argv[1:])
