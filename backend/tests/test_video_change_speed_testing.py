import os
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock

import numpy as np
import apps.video_processor as vcs


class VideoChangeSpeedTestingTests(unittest.TestCase):
    def test_remove_extension(self):
        self.assertEqual(vcs.remove_extension("sample.mp4"), "sample")
        self.assertEqual(vcs.remove_extension("archive.tar.gz"), "archive.tar")

    def test_create_subfolder_idempotent(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            vcs.create_subfolder(tmpdir, "demo")
            vcs.create_subfolder(tmpdir, "demo")
            self.assertTrue(os.path.isdir(os.path.join(tmpdir, "demo")))

    def test_get_recent_video_files_sorted_and_limited(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            old_file = Path(tmpdir) / "old.mp4"
            new_file = Path(tmpdir) / "new.mov"
            ignored_file = Path(tmpdir) / "note.txt"

            old_file.write_text("x")
            time.sleep(0.01)
            new_file.write_text("x")
            ignored_file.write_text("x")

            recent = vcs.get_recent_video_files(tmpdir, 1)
            self.assertEqual(recent, [str(new_file)])

    def test_get_recent_video_files_should_include_mpg(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            mpg_file = Path(tmpdir) / "legacy.mpg"
            mpg_file.write_text("x")

            recent = vcs.get_recent_video_files(tmpdir, 10)
            self.assertIn(str(mpg_file), recent)

    def test_get_recent_video_files_should_include_common_modern_extensions(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            m4v_file = Path(tmpdir) / "clip.m4v"
            webm_file = Path(tmpdir) / "clip.webm"
            mts_file = Path(tmpdir) / "clip.MTS"
            m4v_file.write_text("x")
            webm_file.write_text("x")
            mts_file.write_text("x")

            recent = vcs.get_recent_video_files(tmpdir, 10)
            self.assertIn(str(m4v_file), recent)
            self.assertIn(str(webm_file), recent)
            self.assertIn(str(mts_file), recent)

    def test_get_recent_video_files_should_exclude_generated_speed_outputs(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            source_file = Path(tmpdir) / "piece.mp4"
            generated_60 = Path(tmpdir) / "piece_60.mp4"
            generated_90 = Path(tmpdir) / "piece_90.mp4"
            normal_file = Path(tmpdir) / "piece_95.mp4"

            source_file.write_text("x")
            generated_60.write_text("x")
            generated_90.write_text("x")
            normal_file.write_text("x")

            recent = vcs.get_recent_video_files(tmpdir, 10)
            self.assertIn(str(source_file), recent)
            self.assertIn(str(normal_file), recent)
            self.assertNotIn(str(generated_60), recent)
            self.assertNotIn(str(generated_90), recent)

    def test_is_file_ready_returns_true_for_stable_readable_file(self):
        with mock.patch.object(vcs.os.path, "exists", return_value=True), \
             mock.patch.object(vcs.os.path, "getsize", side_effect=[1024, 1024]), \
             mock.patch.object(vcs.os.path, "getmtime", side_effect=[111.0, 111.0]), \
             mock.patch.object(vcs.time, "sleep"), \
             mock.patch.object(vcs, "VideoFileClip") as clip_ctor:
            clip = mock.Mock()
            clip.duration = 5.0
            clip_ctor.return_value = clip

            ready = vcs.is_file_ready("video.mp4", checks=2, interval_seconds=0)

        self.assertTrue(ready)
        clip.close.assert_called_once()

    def test_is_file_ready_returns_false_when_file_is_changing(self):
        with mock.patch.object(vcs.os.path, "exists", return_value=True), \
             mock.patch.object(vcs.os.path, "getsize", side_effect=[1024, 2048]), \
             mock.patch.object(vcs.os.path, "getmtime", side_effect=[111.0, 112.0]), \
             mock.patch.object(vcs.time, "sleep"):
            ready = vcs.is_file_ready("video.mp4", checks=2, interval_seconds=0)

        self.assertFalse(ready)

    def test_processvideo_calls_pipeline_for_all_speed_factors(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            old_cwd = os.getcwd()
            os.chdir(tmpdir)
            try:
                Path("input.mp4").write_text("x")

                with mock.patch.object(vcs, "directory", "./"), \
                     mock.patch.object(vcs, "separate_video_audio") as separate_mock, \
                     mock.patch.object(vcs, "combine_video_audio") as combine_mock, \
                     mock.patch.object(vcs.os.path, "exists", return_value=False), \
                     mock.patch.object(vcs.shutil, "move") as move_mock:
                    vcs.processvideo("input.mp4")

                self.assertEqual(separate_mock.call_count, 4)
                self.assertEqual(combine_mock.call_count, 4)
                self.assertEqual(move_mock.call_count, 5)

                speed_factors = [call.args[1] for call in separate_mock.call_args_list]
                self.assertEqual(speed_factors, [0.6, 0.7, 0.8, 0.9])

                temp_audio_names = [call.args[2] for call in separate_mock.call_args_list]
                self.assertEqual(len(set(temp_audio_names)), 4)
                self.assertTrue(all(name.endswith(".wav") for name in temp_audio_names))

                output_names = [call.args[2] for call in combine_mock.call_args_list]
                self.assertEqual(
                    output_names,
                    ["input_60.mp4", "input_70.mp4", "input_80.mp4", "input_90.mp4"],
                )

                moved_sources = [call.args[0] for call in move_mock.call_args_list]
                self.assertEqual(
                    moved_sources,
                    [
                        "input_60.mp4",
                        "input_70.mp4",
                        "input_80.mp4",
                        "input_90.mp4",
                        "input.mp4",
                    ],
                )
            finally:
                os.chdir(old_cwd)

    def test_processvideo_normalizes_dot_slash_input_path(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            old_cwd = os.getcwd()
            os.chdir(tmpdir)
            try:
                Path("input.mp4").write_text("x")

                with mock.patch.object(vcs, "directory", "./"), \
                     mock.patch.object(vcs, "separate_video_audio"), \
                     mock.patch.object(vcs, "combine_video_audio"), \
                     mock.patch.object(vcs.os.path, "exists", return_value=False), \
                     mock.patch.object(vcs.shutil, "move") as move_mock:
                    vcs.processvideo("./input.mp4")

                moved_targets = [call.args[1] for call in move_mock.call_args_list]
                self.assertTrue(all("././" not in target for target in moved_targets))
                self.assertEqual(moved_targets[-1], "./input_BianSu/input.mp4")
            finally:
                os.chdir(old_cwd)

    def test_processvideo_cleans_temp_files_when_they_exist(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            old_cwd = os.getcwd()
            os.chdir(tmpdir)
            try:
                Path("input.mp4").write_text("x")

                with mock.patch.object(vcs, "directory", "./"), \
                     mock.patch.object(vcs, "separate_video_audio"), \
                     mock.patch.object(vcs, "combine_video_audio"), \
                     mock.patch.object(vcs.os.path, "exists", return_value=True), \
                     mock.patch.object(vcs.os, "remove") as remove_mock, \
                     mock.patch.object(vcs.shutil, "move"):
                    vcs.processvideo("input.mp4")

                self.assertEqual(remove_mock.call_count, 12)
                removed_files = [call.args[0] for call in remove_mock.call_args_list]
                self.assertEqual(len(set(removed_files)), 12)
                self.assertTrue(all(name.startswith("temp_input_") for name in removed_files))
            finally:
                os.chdir(old_cwd)

    def test_processvideo_removes_existing_output_folder_before_regeneration(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            old_cwd = os.getcwd()
            os.chdir(tmpdir)
            try:
                Path("input.mp4").write_text("x")
                existing_output_dir = Path(tmpdir) / "input_BianSu"
                existing_output_dir.mkdir(parents=True, exist_ok=True)
                (existing_output_dir / "old_result.mp4").write_text("old")

                with mock.patch.object(vcs, "directory", "./"), \
                     mock.patch.object(vcs, "separate_video_audio"), \
                     mock.patch.object(vcs, "combine_video_audio"), \
                     mock.patch.object(vcs.os.path, "exists", return_value=False), \
                     mock.patch.object(vcs.shutil, "rmtree", wraps=vcs.shutil.rmtree) as rmtree_mock, \
                     mock.patch.object(vcs.shutil, "move"):
                    vcs.processvideo("input.mp4")

                rmtree_mock.assert_called_once()
                removed_path = str(rmtree_mock.call_args.args[0])
                self.assertTrue(removed_path.endswith("input_BianSu"))
            finally:
                os.chdir(old_cwd)

    def test_processvideo_cleans_temp_files_when_processing_errors(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            old_cwd = os.getcwd()
            os.chdir(tmpdir)
            try:
                Path("input.mp4").write_text("x")

                with mock.patch.object(vcs, "directory", "./"), \
                     mock.patch.object(vcs, "separate_video_audio", side_effect=RuntimeError("boom")), \
                     mock.patch.object(vcs.os.path, "exists", return_value=True), \
                     mock.patch.object(vcs.os, "remove") as remove_mock:
                    with self.assertRaises(RuntimeError):
                        vcs.processvideo("input.mp4")

                removed_files = [call.args[0] for call in remove_mock.call_args_list]
                self.assertEqual(len(removed_files), 3)
                self.assertTrue(all(name.startswith("temp_input_60") for name in removed_files))
            finally:
                os.chdir(old_cwd)

    def test_stretch_audio_silent_input_should_not_output_nan_or_inf(self):
        librosa_mock = mock.Mock()
        librosa_mock.load.return_value = (np.zeros(8), 44100)
        librosa_mock.stft.return_value = np.zeros(8, dtype=np.complex128)
        librosa_mock.phase_vocoder.return_value = np.zeros(8, dtype=np.complex128)
        librosa_mock.istft.return_value = np.zeros(8)

        sf_mock = mock.Mock()

        with mock.patch.object(vcs, "librosa", librosa_mock), \
             mock.patch.object(vcs, "sf", sf_mock):
            vcs.stretch_audio("in.mp3", "out.wav", 0.8)

        written_audio = sf_mock.write.call_args.args[1]
        self.assertTrue(np.all(np.isfinite(written_audio)))

    def test_separate_video_audio_closes_clips_on_write_error(self):
        source_video = mock.Mock()
        source_audio = mock.Mock()
        source_video.audio = source_audio
        muted_video = mock.Mock()
        rendered_video = mock.Mock()
        source_video.set_audio.return_value = muted_video
        muted_video.speedx.return_value = rendered_video
        rendered_video.write_videofile.side_effect = RuntimeError("write failed")

        with mock.patch.object(vcs, "VideoFileClip", return_value=source_video), \
             mock.patch.object(vcs, "stretch_audio"):
            with self.assertRaises(RuntimeError):
                vcs.separate_video_audio("in.mp4", 0.8, "a.wav", "temp.mp3", "temp.mp4")

        source_audio.close.assert_called_once()
        rendered_video.close.assert_called_once()

    def test_separate_video_audio_emits_step_progress(self):
        source_video = mock.Mock()
        source_audio = mock.Mock()
        source_video.audio = source_audio
        muted_video = mock.Mock()
        rendered_video = mock.Mock()
        source_video.set_audio.return_value = muted_video
        muted_video.speedx.return_value = rendered_video

        progress_events = []

        with mock.patch.object(vcs, "VideoFileClip", return_value=source_video), \
             mock.patch.object(vcs, "stretch_audio"):
            vcs.separate_video_audio(
                "in.mp4",
                0.8,
                "a.wav",
                "temp.mp3",
                "temp.mp4",
                progress_callback=lambda stage: progress_events.append(stage),
            )

        self.assertEqual(progress_events, ["extract-audio", "stretch-audio", "render-video"])

    def test_combine_video_audio_closes_clips_on_write_error(self):
        source_video = mock.Mock()
        source_audio = mock.Mock()
        mixed_video = mock.Mock()
        source_video.set_audio.return_value = mixed_video
        mixed_video.write_videofile.side_effect = RuntimeError("write failed")

        with mock.patch.object(vcs, "VideoFileClip", return_value=source_video), \
             mock.patch.object(vcs, "AudioFileClip", return_value=source_audio):
            with self.assertRaises(RuntimeError):
                vcs.combine_video_audio("v.mp4", "a.wav", "out.mp4")

        source_audio.close.assert_called_once()
        mixed_video.close.assert_called_once()

    def test_main_changes_to_video_directory_before_processing(self):
        with mock.patch.object(vcs.os, "chdir") as chdir_mock, \
             mock.patch.object(vcs, "get_recent_video_files", return_value=["a.mp4"]) as list_mock, \
             mock.patch.object(vcs, "is_file_ready", return_value=True), \
             mock.patch.object(vcs, "probe_media_file", return_value=(True, None)), \
             mock.patch.object(vcs, "processvideo") as process_mock:
            vcs.main()

        chdir_mock.assert_called_once_with(vcs.VIDEO_DIRECTORY)
        list_mock.assert_called_once_with("./", vcs.NUM_FILES)
        process_mock.assert_called_once_with("a.mp4")

    def test_main_continues_processing_when_one_file_fails(self):
        with mock.patch.object(vcs.os, "chdir"), \
             mock.patch.object(vcs, "get_recent_video_files", return_value=["a.mp4", "b.mp4"]), \
             mock.patch.object(vcs, "is_file_ready", return_value=True), \
             mock.patch.object(vcs, "probe_media_file", return_value=(True, None)), \
             mock.patch.object(vcs, "processvideo", side_effect=[RuntimeError("boom"), None]) as process_mock:
            vcs.main()

        self.assertEqual([call.args[0] for call in process_mock.call_args_list], ["a.mp4", "b.mp4"])

    def test_main_accepts_directory_from_cli_argument(self):
        custom_directory = "/tmp/custom-videos"
        with mock.patch.object(vcs.os, "chdir") as chdir_mock, \
             mock.patch.object(vcs, "get_recent_video_files", return_value=[]) as list_mock:
            vcs.main(["--directory", custom_directory])

        chdir_mock.assert_called_once_with(custom_directory)
        list_mock.assert_called_once_with("./", vcs.NUM_FILES)

    def test_main_skips_files_that_are_not_ready(self):
        with mock.patch.object(vcs.os, "chdir"), \
             mock.patch.object(vcs, "get_recent_video_files", return_value=["a.mp4", "b.mp4"]), \
             mock.patch.object(vcs, "is_file_ready", side_effect=[False, True]), \
             mock.patch.object(vcs, "probe_media_file", return_value=(True, None)), \
             mock.patch.object(vcs, "processvideo") as process_mock:
            vcs.main()

        process_mock.assert_called_once_with("b.mp4")

    def test_main_uses_file_readiness_constants(self):
        with mock.patch.object(vcs.os, "chdir"), \
             mock.patch.object(vcs, "get_recent_video_files", return_value=["a.mp4"]), \
             mock.patch.object(vcs, "is_file_ready", return_value=True) as ready_mock, \
             mock.patch.object(vcs, "probe_media_file", return_value=(True, None)), \
             mock.patch.object(vcs, "processvideo"):
            vcs.main()

        ready_mock.assert_called_once_with(
            "a.mp4",
            checks=vcs.FILE_READY_CHECKS,
            interval_seconds=vcs.FILE_READY_INTERVAL_SECONDS,
        )

    def test_probe_media_file_returns_false_when_missing_audio_stream(self):
        ffprobe_output = '{"streams":[{"codec_type":"video"}]}'
        completed = mock.Mock(returncode=0, stdout=ffprobe_output, stderr="")
        with mock.patch.object(vcs.subprocess, "run", return_value=completed):
            ok, reason = vcs.probe_media_file("a.mp4")

        self.assertFalse(ok)
        self.assertIn("audio", reason.lower())

    def test_probe_media_file_returns_false_when_ffprobe_not_found(self):
        with mock.patch.object(vcs.subprocess, "run", side_effect=FileNotFoundError("ffprobe")):
            ok, reason = vcs.probe_media_file("a.mp4")

        self.assertFalse(ok)
        self.assertIn("ffprobe", reason.lower())

    def test_resolve_ffprobe_bin_prefers_environment_variable(self):
        with mock.patch.dict(vcs.os.environ, {"FFPROBE_BIN": "/custom/ffprobe"}, clear=False):
            self.assertEqual(vcs.resolve_ffprobe_bin(), "/custom/ffprobe")

    def test_main_skips_file_when_media_probe_fails(self):
        with mock.patch.object(vcs.os, "chdir"), \
             mock.patch.object(vcs, "get_recent_video_files", return_value=["a.mp4"]), \
             mock.patch.object(vcs, "is_file_ready", return_value=True), \
             mock.patch.object(vcs, "probe_media_file", return_value=(False, "missing audio")), \
             mock.patch.object(vcs, "processvideo") as process_mock:
            vcs.main()

        process_mock.assert_not_called()


if __name__ == "__main__":
    unittest.main()
