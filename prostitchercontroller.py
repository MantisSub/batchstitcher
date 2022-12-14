#!/usr/bin/python3
# -*- coding: utf-8 -*-
"""
Stitch multiple VID_xxx recording projects captured with Insta360 Pro 2
"""

__author__ = "Axel Busch"
__copyright__ = "Copyright 2022, Xlvisuals Limited"
__license__ = "GPL-2.1"
__version__ = "0.0.3"
__email__ = "info@xlvisuals.com"

import sys
import copy
import os.path
import tempfile
import subprocess
import shlex
import threading
import queue
import json
import xml.etree.ElementTree as et
from time import localtime, strftime, time, sleep
from helpers import Helpers


class ProStitcherController:

    ignore_entries = [".DS_store", "__pycache__"]

    DEFAULT_STITCHER_MAC = "/Applications/Insta360Stitcher.app/Contents/Resources/tools/ProStitcher/ProStitcher"
    DEFAULT_STITCHER_SUBDIR_MAC = "Contents/Resources/tools/ProStitcher/ProStitcher"
    DEFAULT_FFPROBE_MAC = "ffprobe"
    DEFAULT_STITCHER_WIN = 'C:/Program Files (x86)/Insta360Stitcher/tools/prostitcher/ProStitcher.exe'
    DEFAULT_STITCHER_SUBDIR_WIN = "tools/prostitcher/ProStitcher.exe'"
    DEFAULT_FFPROBE_WIN = "ffprobe.exe"

    default_settings = {
        "source_filter": "VID_",
        "threads": 1,
        "source_dir": "",
        "target_dir": "",
        "ffprobe_path": "ffprobe.exe",
        "stitcher_path": "C:/Program Files (x86)/Insta360Stitcher/tools/prostitcher/ProStitcher.exe",
        "encode_use_hardware": 0,
        "decode_use_hardware": 1,
        "decode_use_hardware_count": 6,
        "blend_mode": "pano",
        "output_codec": "h264",
        "output_format": "mp4",
        "width": 7680,
        "bitrate": 251658240,
        "min_recording_duration": 15,
        "rename_after_stitching": True,
        "rename_prefix": "_",
        "trim_start": 10,
        "trim_end": -5,
        "blender_type": "auto",
        "zenith_optimisation": 0,
        "flowstate_stabilisation": 1,
        "original_offset": 1,
        "smooth_stitch": 1,
        "brightness": 0,
        "contrast": 0,
        "highlight": 0,
        "shadow": 0,
        "saturation": 0,
        "temperature": 0,
        "tint": 0,
        "sharpness": 0,
        "audio_type": "pano",
        "sampling_level": "medium",
        "encode_preset": "veryfast",
        "encode_profile": "main",
        "output_fps": "29.97",
        "roll_x": 0.0,
        "tilt_y": 0.0,
        "pan_z": 0.0,
        "reference_time": 0
    }

    default_parameters = {
        "source_dir": "",
        "target_dir": "",
        "project_dir": "",
        "trim_start": 10,
        "trim_end": -5,
        "blender_type": "auto",  
        "blend_capture_time": "10",
        "blend_use_optical_flow": "1",
        "blend_new_optical_flow": "1",
        "blend_angle_template": "0.5",
        "blend_top_fixer": "0",
        "blend_angle_optical": "20",  
        "blend_mode": "pano",  
        "blend_smooth_stitch": "true",
        "blend_original_offset": "true",
        "blend_vr180_lens_selection": "<lensSelection/>",  
        "blend_vr180_yaw": '',  
        "encode_use_hardware": "0",
        "decode_use_hardware": "1",
        "decode_use_hardware_count": "6",  
        "gyro_enable": 1,
        "gyro_flowstate_enable": "true",
        "color_brightness": "0",
        "color_contrast": "10",
        "color_highlight": "3",
        "color_shadow": "5",
        "color_saturation": "5",
        "color_temperature": "0",
        "color_tint": "0",
        "color_sharpness": "85",
        "output_width": "7680",
        "output_height": "3840",  
        "output_destination": "",
        "output_type": "video",
        "output_bitrate": "251658240",
        "output_fps": "29.97",
        "output_interpolation": "0",
        "output_codec": "h264",
        "output_format": "mp4",
        "output_audio_type": "pano",
        "output_audio_device": "insta360",
        "gps_latitude": "0",
        "gps_longitude": "0",
        "gps_altitude": "0",
        "encode_preset": "superfast",
        "encode_profile": "baseline",
        "sampling_level": "fast",
        "diff_quat_x": 0,
        "diff_quat_y": 0,
        "diff_quat_z": 0,
        "diff_quat_w": 1
    }

    vr180_lens_selection = """
        <lensSelection>
          <leftEye>
            <selection value="false"/>
            <selection value="false"/>
            <selection value="true"/>
            <selection value="false"/>
            <selection value="false"/>
            <selection value="false"/>
          </leftEye>
          <rightEye>
            <selection value="false"/>
            <selection value="false"/>
            <selection value="false"/>
            <selection value="true"/>
            <selection value="false"/>
            <selection value="false"/>
          </rightEye>
        </lensSelection>
    """

    default_template = \
        """<stitchParam>
      <input type="video" lensCount="6" fileCount="1" generation="pro2" fwVersion="1.1.8">
        <stitching enable="both"/>
        <videoGroup type="h264" ptsOffset="0" enable="1">
          <trim start="$TRIM_START" end="$TRIM_END"/>
          <file src="$RECORDING_DIR/origin_6.mp4"/>
          <file src="$RECORDING_DIR/origin_5.mp4"/>
          <file src="$RECORDING_DIR/origin_4.mp4"/>
          <file src="$RECORDING_DIR/origin_3.mp4"/>
          <file src="$RECORDING_DIR/origin_2.mp4"/>
          <file src="$RECORDING_DIR/origin_1.mp4"/>
        </videoGroup>
        <audio src="$RECORDING_DIR/origin_6_lrv.mp4"/>
      </input>
      <blend useOpticalFlow="$BLEND_USE_OPTICAL_FLOW" useNewOpticalFlow="$BLEND_NEW_OPTICAL_FLOW" mode="$BLEND_MODE" samplingLevel="$SAMPLING_LEVEL" useTopFixer="$BLEND_TOP_FIXER" opticalBlendAngle="$BLEND_ANGLE_OPTICAL" templateBlendAngle="$BLEND_ANGLE_TEMPLATE" enableColorAdjustment="$BLEND_SMOOTH_STITCH" useOriginalOffset="$BLEND_ORIGINAL_OFFSET" $BLEND_VR180_YAW>
        <capture time="$BLEND_CAPTURE_TIME" index="0"/>
        <offset sourceCropType="1">
          <pano>$OFFSET_PANO</pano>
          <stereoLeft>$OFFSET_STEREO_LEFT</stereoLeft>
          <stereoRight>$OFFSET_STEREO_RIGHT</stereoRight>
        </offset>
        $BLEND_LENS_SELECTION
      </blend>
      <preference auto="true">
        <encode useHardware="$ENCODE_USE_HARDWARE" threads="4" preset="$ENCODE_PRESET" profile="$ENCODE_PROFILE"/>
        <decode useHardware="$DECODE_USE_HARDWARE" count="6" threads="4"/>
        <blender type="$BLENDER_TYPE" hdrPreferSaturation="false"/>
      </preference>
      <gyro version="4" storage_type="camm" type="pro_flowstate" enableFlowstate="$GYRO_FLOWSTATE_ENABLE" sweepTime="21478.775024" delayTime="83000" enable="$GYRO_ENABLE" filter="akf">
        <sts_group>
          <start_ts>$START_TS_1</start_ts>
          <start_ts>$START_TS_2</start_ts>
          <start_ts>$START_TS_3</start_ts>
          <start_ts>$START_TS_4</start_ts>
          <start_ts>$START_TS_5</start_ts>
          <start_ts>$START_TS_6</start_ts>
        </sts_group>
        <timeOffset>$START_TS_1</timeOffset>
        <files>
          <file src="$RECORDING_DIR/origin_6_lrv.mp4"/>
        </files>
        <imu_rotation x="1" y="0" z="0" w="0"/>
        <calibration gravity_x="$GRAVITY_X" gravity_y="$GRAVITY_Y" gravity_z="$GRAVITY_Z"/>
        <angle diff_pan="0" diff_tilt="0" diff_roll="0" diff_quatx="$DIFF_QUAT_X" diff_quaty="$DIFF_QUAT_Y" diff_quatz="$DIFF_QUAT_Z" diff_quatw="$DIFF_QUAT_W" distance="603.3333333333334"/>
      </gyro>
      <color brightness="$COLOR_BRIGHTNESS" contrast="$COLOR_CONTRAST" highlight="$COLOR_HIGHLIGHT" shadow="$COLOR_SHADOW" saturation="$COLOR_SATURATION" tempture="$COLOR_TEMPERATURE" tint="$COLOR_TINT" sharpness="$COLOR_SHARPNESS"/>
      <depthMap enable="0" path="" inverse="1"/>
      <output width="$OUTPUT_WIDTH" height="$OUTPUT_HEIGHT" dst="$OUTPUT_DESTINATION" type="$OUTPUT_TYPE">
        <video fps="$OUTPUT_FPS" codec="$OUTPUT_CODEC" bitrate="$OUTPUT_BITRATE" useInterpolation="$OUTPUT_INTERPOLATION"/>
        <audio type="$OUTPUT_AUDIO_TYPE" device="$OUTPUT_AUDIO_DEVICE"/>
      </output>
      <gps>
        <data status="0" latitude="0" longitude="0" altitude="0" v_accuracy="0" h_accuracy="0" velocity_east="0" velocity_north="0" velocity_up="0" speed_accuracy="0"/>
      </gps>
    </stitchParam>
    """

    def __init__(self):
        self.settings = {}
        self.log_callback = None
        self.done_callback = None
        self.q = queue.Queue()
        self._stopping = False

    def _run_prostitcher(self, prostitcher, workingdir, templatefile, logfile):
        returncode = -1
        try:
            cmd = f'"{prostitcher}" -l "{logfile}" -w stitch -x "{templatefile}"'
            args = shlex.split(cmd)

            if sys.platform == "win32":
                # Hide console
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                p = subprocess.Popen(args,
                                     cwd=workingdir,
                                     shell=False,
                                     startupinfo=startupinfo,
                                     stdout=subprocess.DEVNULL,
                                     stderr=subprocess.DEVNULL,
                                     )
            else:
                p = subprocess.Popen(args,
                                     cwd=workingdir,
                                     shell=False,
                                     stdout=subprocess.DEVNULL,
                                     stderr=subprocess.DEVNULL,
                                     )
            if p:
                while True:
                    returncode = p.poll()
                    if returncode is None:
                        if self._stopping:
                            self._log_info("Terminating stitching. ")
                            p.terminate()
                            self._log_info("Stitching terminated. ")
                            break
                        else:
                            sleep(0.5)
                            self._log_info(".")
                    else:
                        if returncode != 0:
                            explanation = ''
                            if returncode == -6:
                                explanation = "Not all origin_x.mp4 files present."
                            elif returncode == 235:
                                explanation = "Source video not found."
                            elif returncode == 244:
                                if self.settings["encode_use_hardware"]:
                                    explanation = "Hardware encoding not supported."
                                else:
                                    explanation = "Codec/Profile not supported."
                            elif returncode == 4294967295:
                                explanation = "Wrong output file format."
                            if explanation:
                                self._log_info(f"WARNING. ProStitcher returned code {returncode} ({explanation}).\n"
                                               f"    ProStitcher: {prostitcher}\n"
                                               f"    Template: {templatefile}\n"
                                               f"    Logfile: {logfile}\n")
                            else:
                                self._log_info(f"WARNING. ProStitcher returned code {returncode}.\n"
                                               f"    ProStitcher: {prostitcher}\n"
                                               f"    Template: {templatefile}\n"
                                               f"    Logfile: {logfile}\n")

                        break
        except OSError as e:
            self._log_error("Error running prostitcher: {}".format(str(e)))
        except subprocess.CalledProcessError as e:
            self._log_error("Error running prostitcher: {}".format(str(e)))
        return returncode

    def _run_ffprobe(self, ffprobe, filename):
        """
        returns duration, fps
        """
        duration = 0
        fps = 0
        try:
            result = subprocess.check_output(
                f'"{ffprobe}" -v quiet -show_streams -select_streams v:0 -of json "{filename}"',
                shell=True).decode()
            fields = json.loads(result)['streams'][0]
            # Other fields:
            # fields['codec_name'], fields['profile'], fields['width'], fields['height'],
            # fields['bit_rate'], fields['tags']["creation_time"]
            duration = float(fields['duration'])
            fps = str(round(eval(fields['r_frame_rate']), 2))
        except OSError as e:
            self._log_error("Error running ffprobe: {}".format(str(e)))
        except subprocess.CalledProcessError as e:
            self._log_error("Error running ffprobe: {}".format(str(e)))
        return duration, fps


    def update_template(self, recording_name, duration, input_fps, recording_project_data, output_destination):
        project = et.fromstring(recording_project_data)
        gravity_x = str(round(float(project.find("./gyro/calibration/gravity_x").text), 6))
        gravity_y = str(round(float(project.find("./gyro/calibration/gravity_y").text), 6))
        gravity_z = str(round(float(project.find("./gyro/calibration/gravity_z").text), 6))
        offset_pano = project.find("./origin_offset/pano_4_3").text
        offset_stereo_left = project.find("./origin_offset/pano_4_3").text
        offset_stereo_right = project.find("./origin_offset/pano_16_9").text
        start_ts_1 = project.find("./gyro/sts_group")[0].text
        start_ts_2 = project.find("./gyro/sts_group")[1].text
        start_ts_3 = project.find("./gyro/sts_group")[2].text
        start_ts_4 = project.find("./gyro/sts_group")[3].text
        start_ts_5 = project.find("./gyro/sts_group")[4].text
        start_ts_6 = project.find("./gyro/sts_group")[5].text

        # update template parameters
        recording_parameters = copy.deepcopy(ProStitcherController.default_parameters)
        recording_parameters["source_dir"] = self.settings["source_dir"]
        recording_parameters["target_dir"] = self.settings["target_dir"]
        recording_parameters["recording_dir"] = os.path.join(self.settings["source_dir"], recording_name)
        recording_parameters["output_destination"] = output_destination
        recording_parameters["recording_name"] = recording_name
        if self.settings["trim_start"] < 0 or self.settings["trim_start"] > duration:
            self.settings["trim_start"] = 0
        else:
            recording_parameters["trim_start"] = self.settings["trim_start"]
        if self.settings["trim_end"] < 0:
            recording_parameters["trim_end"] = duration + self.settings["trim_end"]
            if recording_parameters["trim_end"] < 0:
                recording_parameters["trim_end"] = duration
        elif 0 < self.settings["trim_end"] < duration:
            recording_parameters["trim_end"] = self.settings["trim_end"]
        else:
            recording_parameters["trim_end"] = duration
        recording_parameters["gravity_x"] = gravity_x
        recording_parameters["gravity_y"] = gravity_y
        recording_parameters["gravity_z"] = gravity_z
        recording_parameters["offset_pano"] = offset_pano
        recording_parameters["offset_stereo_left"] = offset_stereo_left
        recording_parameters["offset_stereo_right"] = offset_stereo_right
        recording_parameters["start_ts_1"] = start_ts_1
        recording_parameters["start_ts_2"] = start_ts_2
        recording_parameters["start_ts_3"] = start_ts_3
        recording_parameters["start_ts_4"] = start_ts_4
        recording_parameters["start_ts_5"] = start_ts_5
        recording_parameters["start_ts_6"] = start_ts_6

        try:
            qx, qy, qz, qw = Helpers.euler_degrees_to_quaternion(self.settings["roll_x"],
                                                                 self.settings["tilt_y"],
                                                                 self.settings["pan_z"],
                                                                 y_up=True)
            recording_parameters["diff_quat_x"] = qx
            recording_parameters["diff_quat_y"] = qy
            recording_parameters["diff_quat_z"] = qz
            recording_parameters["diff_quat_w"] = qw
        except:
            recording_parameters["diff_quat_x"] = 0
            recording_parameters["diff_quat_y"] = 0
            recording_parameters["diff_quat_z"] = 0
            recording_parameters["diff_quat_w"] = 1

        # "blend_mode": "pano",  # Mono: pano, Stereo: stereo_top_left, stereo_top_right, vr180, vr180_4lens
        recording_parameters["blend_mode"] = self.settings["blend_mode"]
        if self.settings["blend_mode"] == "vr180":
            recording_parameters["blend_lens_selection"] = ProStitcherController.vr180_lens_selection
            recording_parameters["blend_vr180_yaw"] = ""
            recording_parameters["blend_angle_optical"] = "16"
            recording_parameters["output_width"] = str(int(self.settings["width"]))
            recording_parameters["output_height"] = str(int(self.settings["width"]/2))
        elif self.settings["blend_mode"] == "vr180_4lens":
            recording_parameters["blend_lens_selection"] = "<lensSelection/>"
            recording_parameters["blend_vr180_yaw"] = 'vr180Yaw="180"'
            recording_parameters["blend_angle_optical"] = "16"
            recording_parameters["output_width"] = str(int(self.settings["width"]))
            recording_parameters["output_height"] = str(int(self.settings["width"]/2))
        elif self.settings["blend_mode"] in ["stereo_top_left", "stereo_top_right"]:
            recording_parameters["blend_lens_selection"] = "<lensSelection/>"
            recording_parameters["blend_vr180_yaw"] = ""
            recording_parameters["blend_angle_optical"] = "!6"
            recording_parameters["output_width"] = str(int(self.settings["width"]))
            recording_parameters["output_height"] = str(int(self.settings["width"]/2))
        else:
            recording_parameters["blend_lens_selection"] = "<lensSelection/>"
            recording_parameters["blend_vr180_yaw"] = ""
            recording_parameters["blend_angle_optical"] = "20"
            recording_parameters["output_width"] = str(int(self.settings["width"]))
            recording_parameters["output_height"] = str(int(self.settings["width"]/2))
        recording_parameters["blend_capture_time"] = Helpers.parse_int(self.settings["reference_time"])
        if not recording_parameters["blend_capture_time"] or recording_parameters["blend_capture_time"] > duration or recording_parameters["blend_capture_time"] < 0:
            recording_parameters["blend_capture_time"] = Helpers.parse_int(duration/2)
        recording_parameters["gyro_enable"] = "1" if self.settings["flowstate_stabilisation"] else "0"
        recording_parameters["blend_smooth_stitch"] = "true" if self.settings["smooth_stitch"] else "false"
        recording_parameters["blend_original_offset"] = "true" if self.settings["original_offset"] else "false"
        recording_parameters["blend_top_fixer"] = "1" if self.settings["zenith_optimisation"] else "0"
        recording_parameters["blender_type"] = self.settings["blender_type"] or "auto"
        recording_parameters["encode_preset"] = self.settings["encode_preset"] or "superfast"
        recording_parameters["encode_profile"] = self.settings["encode_profile"] or "baseline"
        recording_parameters["sampling_level"] = self.settings["sampling_level"] or "fast"
        recording_parameters["encode_use_hardware"] = str(self.settings["encode_use_hardware"]) or "0"
        recording_parameters["decode_use_hardware"] = str(self.settings["decode_use_hardware"]) or "1"
        recording_parameters["decode_use_hardware_count"] = self.settings["decode_use_hardware_count"] or "6"
        recording_parameters["output_bitrate"] = str(self.settings["bitrate"]) or "503316480"
        recording_parameters["output_codec"] = self.settings["output_codec"] or "h264"
        recording_parameters["output_format"] = self.settings["output_format"] or "mp4"
        recording_parameters["output_audio_type"] = self.settings["audio_type"] or "pano"
        recording_parameters["output_fps"] = str(self.settings["output_fps"]) or "29.97"
        if Helpers.parse_float(self.settings["output_fps"]) > Helpers.parse_float(input_fps):
            recording_parameters["output_interpolate"] = "1"
        else:
            recording_parameters["output_interpolate"] = "0"
        recording_parameters["color_brightness"] = self.settings["brightness"] or "0"
        recording_parameters["color_contrast"] = self.settings["contrast"] or "0"
        recording_parameters["color_highlight"] = self.settings["highlight"] or "0"
        recording_parameters["color_shadow"] = self.settings["shadow"] or "0"
        recording_parameters["color_saturation"] = self.settings["saturation"] or "0"
        recording_parameters["color_temperature"] = self.settings["temperature"] or "0"
        recording_parameters["color_tint"] = self.settings["tint"] or "0"
        recording_parameters["color_sharpness"] = self.settings["sharpness"] or "0"

        # fix known settings constraints
        if sys.platform == "darwin" and recording_parameters["blender_type"] == "cuda":
            # cuda not supported on mac
            recording_parameters["blender_type"] = "opencl"
        if self.settings["output_codec"] == "prores":
            # prores only supports encode_profile=3
            recording_parameters["encode_profile"] = "3"
            # prores only supports output_format=mov
            recording_parameters["output_format"] = "mov"
        elif self.settings["output_codec"] == "h265" and self.settings["encode_profile"] == "baseline":
            # h265 encoding crashes with encode_profile=baseline. Set encode_profile=main
            recording_parameters["encode_profile"] = "main"

        # replace parameters in template
        recording_template = ProStitcherController.default_template
        for k, v in recording_parameters.items():
            recording_template = recording_template.replace("${}".format(k.upper()), str(v))

        # remove destination file if exists
        try:
            if os.path.exists(recording_parameters["output_destination"]):
                os.remove(recording_parameters["output_destination"])
        except:
            pass

        return recording_template

    def process_recording(self, recording):
        result = -1
        t = strftime("%H%M%S", localtime())

        preview_filepath = os.path.join(self.settings["source_dir"], recording, "preview.mp4")
        duration, fps = self._run_ffprobe(self.settings["ffprobe_path"], preview_filepath)
        if duration >= self.settings["min_recording_duration"]:
            # create file paths
            tempdir = tempfile.gettempdir()
            recording_project_file = os.path.join(self.settings["source_dir"], recording, "pro.prj")
            destination_file = "{}_{}.{}".format(recording, t, self.settings["output_format"])
            output_destination = os.path.join(self.settings["target_dir"], destination_file)
            project_filepath = os.path.join(tempdir, recording + "_{}_project.xml".format(t))
            template_filepath = os.path.join(tempdir, recording + "_{}_template.xml".format(t))
            recording_logfile = os.path.join(tempdir, recording + "_{}_stitcher.log".format(t))

            if self.settings["trim_start"] < 0 or self.settings["trim_start"] > duration:
                self.settings["trim_start"] = 0
            if self.settings["trim_end"] < 0:
                self.settings["trim_end"] = duration + self.settings["trim_end"]
                if self.settings["trim_end"] < 0:
                    self.settings["trim_end"] = duration
            stitching_duration = self.settings["trim_end"] - self.settings["trim_start"]

            # read project file
            if os.path.exists(recording_project_file):
                recording_project_data = Helpers.read_file(recording_project_file)
                Helpers.write_file(project_filepath, recording_project_data)

                # create stitching template for this recording
                recording_template = self.update_template(recording, int(duration), fps, recording_project_data,
                                                          output_destination)
                Helpers.write_file(template_filepath, recording_template)

                # stitch
                self._log_info("Stitching {} (duration: {}s) ".format(recording, int(stitching_duration)))
                if not self._stopping:
                    t1 = time()
                    result = self._run_prostitcher(self.settings["stitcher_path"],
                                         tempdir,
                                         os.path.abspath(template_filepath),
                                         os.path.abspath(recording_logfile))
                    if result == 0:
                        t2 = time()
                        t3 = int(t2 - t1)
                        self._log_info("Completed {} in {}s at {} fps.".format(recording, t3,
                                                                             round(float(fps) * int(stitching_duration) / t3, 2)))

                        if self.settings["rename_after_stitching"]:
                            try:
                                cur_path = os.path.join(self.settings["source_dir"], recording)
                                new_path = os.path.join(self.settings["source_dir"], self.settings["rename_prefix"] + recording)
                                os.rename(cur_path, new_path)
                            except:
                                pass
            else:
                self._log_error("ERROR: Project file pro.prj not found for recording {}".format(recording))
        else:
            self._log_info("Recording {} is too short, skipping.".format(recording))
        return result

    def _worker_func(self):
        while True:
            recording = self.q.get()
            try:
                if recording is not None and not self._stopping:
                    self.process_recording(recording)
            except Exception as e:
                self._log_error("Error processing {}: {}".format(recording, str(e)))
            finally:
                self.q.task_done()
                if recording is None:
                    break

    def _start_workers(self, _worker_pool=3):
        threads = []
        for i in range(_worker_pool):
            if not self._stopping:
                t = threading.Thread(target=self._worker_func)
                if t:
                    t.start()
                    threads.append(t)
        return threads

    def _stop_workers(self, threads):
        for i in threads:
            # _workers are configured to quit after retrieving None from the queue.
            self.q.put(None)
        for t in threads:
            t.join()

    def _prepare_settings(self):
        self.settings["width"] = Helpers.parse_int(self.settings["width"])
        self.settings["threads"] = Helpers.parse_int(self.settings["threads"])
        self.settings["encode_use_hardware"] = Helpers.parse_int(self.settings["encode_use_hardware"])
        self.settings["decode_use_hardware"] = Helpers.parse_int(self.settings["decode_use_hardware"])
        self.settings["width"] = Helpers.parse_int(self.settings["width"])
        self.settings["bitrate"] = Helpers.parse_int(self.settings["bitrate"])
        self.settings["bitrate_mbps"] = int(self.settings["bitrate"]/1024/1024)
        self.settings["min_recording_duration"] = Helpers.parse_int(self.settings["min_recording_duration"])
        self.settings["trim_start"] = Helpers.parse_int(self.settings["trim_start"])
        self.settings["trim_end"] = Helpers.parse_int(self.settings["trim_end"])
        self.settings["zenith_optimisation"] = Helpers.parse_int(self.settings["zenith_optimisation"])
        self.settings["flowstate_stabilisation"] = Helpers.parse_int(self.settings["flowstate_stabilisation"])
        self.settings["original_offset"] = Helpers.parse_int(self.settings["original_offset"])
        self.settings["smooth_stitch"] = Helpers.parse_int(self.settings["smooth_stitch"])
        self.settings["zenith_optimisation"] = Helpers.parse_int(self.settings["zenith_optimisation"])
        self.settings["reference_time"] = Helpers.parse_int(self.settings["reference_time"])
        self.settings["roll_x"] = Helpers.parse_int(self.settings["roll_x"])
        self.settings["tilt_y"] = Helpers.parse_int(self.settings["tilt_y"])
        self.settings["pan_z"] = Helpers.parse_int(self.settings["pan_z"])

    def stitch(self, log_callback=None, done_callback=None):
        self.log_callback = log_callback
        self.done_callback = done_callback
        self._prepare_settings()

        source_dir = self.settings["source_dir"]
        source_filter = self.settings["source_filter"]
        target_dir = self.settings["target_dir"]
        threads = self.settings["threads"]

        self._log_info(f"Starting to stitch recordings in folder '{source_dir}'")

        try:
            if not target_dir:
                target_dir = source_dir
            if not os.path.exists(target_dir):
                os.makedirs(target_dir)
        except Exception as e:
            error = "Error location or creating target directory '{}': {}".format(target_dir, str(e))
            self._log_error(error)
            self._log_info(error)

        recordings = Helpers.get_subdirs(source_dir, source_filter)
        if not recordings:
            self._log_error("No recordings in folder '{}'".format(source_dir))
        else:
            self._log_info(f"Found {len(recordings)} recordings to stitch")

            try:
                _workers = self._start_workers(_worker_pool=threads)
                for r in recordings:
                    if not self._stopping:
                        self.q.put(r)
                self.q.join()  # blocking
                self._stop_workers(_workers)

                self._log_info('Done. \n')
            except Exception as e:
                error = "Error processing recordings: {}".format((e))
                self._log_error(error)

        if self.done_callback:
            self.done_callback()
    
    def _log_info(self, text):
        if self.log_callback:
            self.log_callback("info", text)
        else:
            print(text)

    def _log_error(self, text):
        if self.log_callback:
            self.log_callback("error", text)
        else:
            sys.stderr.write(text)
            sys.stderr.write("\n")

    def stop(self):
        self._stopping = True
