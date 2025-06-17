#!/usr/bin/python3
# -*- coding: utf-8 -*-
"""
Stitch multiple VID_xxx recording projects captured with Insta360 Pro 2
"""

__author__ = "Axel Busch"
__copyright__ = "Copyright 2023-2025, Xlvisuals Limited"
__license__ = "GPL-2.1"
__version__ = "0.0.8"
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
        "decode_hardware_count": 6,
        "decode_use_hardware": 1,
        "blend_mode": "pano",
        "stitching_mode": "New Optical Flow",
        "blend_angle_template": "0.5",
        "blend_angle_optical": "20",
        "output_codec": "h264",
        "output_format": "mp4",
        "width": 7680,
        "bitrate": 251658240,
        "min_recording_duration": 15,
        "rename_after_stitching": True,
        "rename_prefix": "_",
        "trim_start": 10,
        "trim_end": -10,
        "blender_type": "auto",
        "zenith_optimisation": 0,
        "flowstate_stabilisation": 1,
        "direction_lock": 0,
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
        "audio_device": "insta360",
        "sampling_level": "medium",
        "encode_preset": "veryfast",
        "encode_profile": "main",
        "output_fps": "default",
        "roll_x": 0.0,
        "tilt_y": 0.0,
        "pan_z": 0.0,
        "reference_time": 0,
        "logo_path": None,
        "logo_angle": "30",
        "logo_node": ""
    }

    default_parameters = {
        "firmware_version": "1.1.8",
        "trim_start": 0,
        "trim_end": 0,
        "blend_algorithm": "2",
        "blender_type": "auto",
        "blend_capture_time": "10",
        "source_crop_type": "2",
        "blend_use_optical_flow": "1",
        "blend_new_optical_flow": "1",
        "blend_angle_template": "0.5",
        "blend_angle_optical": "20",
        "blend_top_fixer": "0",
        "blend_mode": "pano",
        "blend_smooth_stitch": "true",
        "blend_original_offset": "true",
        "blend_vr180_lens_selection": "<lensSelection/>",  
        "blend_vr180_yaw": '',  
        "encode_use_hardware": "0",
        "decode_hardware_count": "6",
        "decode_use_hardware": "1",
        "gyro_enable": 1,
        "gyro_flowstate_enable": "true",
        "gyro_flowstate_mode": "1",
        "gyro_sweep_time": "21478.775024",
        "gyro_delay_time": "83000",
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
        "diff_quat_w": 1,
        "logo_path": None,
        "logo_angle": "30",
        "logo_node": ""
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

    stitcher_template = \
        """<stitchParam>
      <input type="video" lensCount="6" fileCount="1" generation="pro2" fwVersion="$FIRMWARE_VERSION">
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
      <blend blendAlgorithm="$BLEND_ALGORITHM" useOpticalFlow="$BLEND_USE_OPTICAL_FLOW" useNewOpticalFlow="$BLEND_NEW_OPTICAL_FLOW" mode="$BLEND_MODE" samplingLevel="$SAMPLING_LEVEL" useTopFixer="$BLEND_TOP_FIXER" opticalBlendAngle="$BLEND_ANGLE_OPTICAL" templateBlendAngle="$BLEND_ANGLE_TEMPLATE" enableColorAdjustment="$BLEND_SMOOTH_STITCH" useOriginalOffset="$BLEND_ORIGINAL_OFFSET" $BLEND_VR180_YAW>
        <capture time="$BLEND_CAPTURE_TIME" index="0"/>
        <offset sourceCropType="$SOURCE_CROP_TYPE">
          <pano>$OFFSET_PANO</pano>
          <stereoLeft>$OFFSET_STEREO_LEFT</stereoLeft>
          <stereoRight>$OFFSET_STEREO_RIGHT</stereoRight>
        </offset>
        $BLEND_LENS_SELECTION
      </blend>
      <preference auto="true">
        <encode useHardware="$ENCODE_USE_HARDWARE" threads="4" preset="$ENCODE_PRESET" profile="$ENCODE_PROFILE"/>
        <decode useHardware="$DECODE_USE_HARDWARE" count="$DECODE_HARDWARE_COUNT" threads="4"/>
        <blender type="$BLENDER_TYPE" hdrPreferSaturation="false"/>
      </preference>
      <gyro version="4" storage_type="camm" type="pro_flowstate" enableFlowstate="$GYRO_FLOWSTATE_ENABLE" flowstate_mode="$GYRO_FLOWSTATE_MODE" sweepTime="$GYRO_SWEEP_TIME" delayTime="$GYRO_DELAY_TIME" enable="$GYRO_ENABLE" filter="akf">
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
      $LOGO_NODE
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

    def _run_prostitcher(self, prostitcher, workingdir, templatefile, logfile, parametersfile):
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
                            sleep(1)
                            self._log_info(".")
                    else:
                        if returncode != 0:
                            explanation = ''
                            resolution = ''
                            if returncode == -6:
                                explanation = "Not all origin_x.mp4 files present"
                            elif returncode == 235:
                                explanation = "Source video not found"
                            elif returncode == 244:
                                if self.settings["encode_use_hardware"]:
                                    explanation = "Hardware encoding not supported"
                                    resolution = "Please unset 'Use hardware encoding' and try again."
                                else:
                                    explanation = "Codec/Profile/Bitrate combination not supported by hardware"
                                    resolution = "Please try again with different settings for Codec/Profile/Bitrate."
                            elif returncode == 1003:
                                explanation = "'No such file or directory' error looking for origin files"
                                resolution = "Please make sure your origin files have the original file names (origin_1.mp4 etc.), and that the path has no special characters."
                            elif returncode == 1012:
                                explanation = "'File format', 'Codec type' and 'Use hardware encoding' settings are not compatible"
                                resolution = "Please try again with different settings for 'File format', 'Codec type' and 'Use hardware encoding'."
                            elif returncode == 4294967295 or returncode == -11:
                                explanation = "Wrong output file format or audio type, or logo not found."
                                resolution = "Please change the output file format and check the logo path, then try again."
                            if explanation:
                                self._log_info(f"ERROR. ProStitcher returned code {returncode} ({explanation}).")
                            else:
                                self._log_info(f"ERROR. ProStitcher returned code {returncode}.")
                            if resolution:
                                self._log_info(f"{resolution}\n")

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

    @classmethod
    def get_prostitcher_major_version(cls, prostitcher_path):
        """
        Prostitcher Windows v2.5.1: Size = 24M, 25060352
        Prostitcher Windows v3.0.0: Size = 16M, 16182272
        Prostitcher Windows v3.1.2: Size = 29M, 30345216
        Prostitcher Windows v3.1.3: Size = 39M, 40261632
        Prostitcher Windows v4.0.0: Size = 61M, 63691264

        Prostitcher macOS v2.5.1: Size = 13M, 13295556
        Prostitcher macOS v3.0.0: Size = 21M, 22406044
        Prostitcher macOS v4.0.0: Size = 46M, 48142560
        """
        major_version = 3  # default
        try:
            if prostitcher_path and os.path.exists(prostitcher_path):
                size = os.path.getsize(prostitcher_path)
                if sys.platform == "darwin":
                    #macOS
                    if size < 20000000:
                        major_version = 2
                    elif size < 30000000:
                        major_version = 3
                    elif size < 50000000:
                        major_version = 4
                else:
                    # windows
                    if 22000000 < size < 28000000:
                        major_version = 2
                    elif size < 50000000:
                        major_version = 3
                    elif size < 70000000:
                        major_version = 4
        except:
            pass
        return major_version

    def update_template(self, recording_settings, recording_name, duration, input_fps, recording_project_data, output_destination):
        try:
            project = et.fromstring(recording_project_data)
            gravity_x = str(round(float(project.find("./gyro/calibration/gravity_x").text), 6))
            gravity_y = str(round(float(project.find("./gyro/calibration/gravity_y").text), 6))
            gravity_z = str(round(float(project.find("./gyro/calibration/gravity_z").text), 6))
            rolling_shutter_time_us = project.find("./gyro").attrib['rolling_shutter_time_us']
            delay_time_us = project.find("./gyro").attrib['delay_time_us']
            offset_pano = project.find("./origin_offset/pano_4_3").text
            offset_stereo_left = project.find("./origin_offset/pano_4_3").text
            offset_stereo_right = project.find("./origin_offset/pano_16_9").text
            start_ts_1 = project.find("./gyro/sts_group")[0].text
            start_ts_2 = project.find("./gyro/sts_group")[1].text
            start_ts_3 = project.find("./gyro/sts_group")[2].text
            start_ts_4 = project.find("./gyro/sts_group")[3].text
            start_ts_5 = project.find("./gyro/sts_group")[4].text
            start_ts_6 = project.find("./gyro/sts_group")[5].text
            audio_device = project.find("./audio").attrib['audio_device']
            spatial_audio = project.find("./audio").attrib['spatial_audio']
            audio_file = project.find("./audio").attrib['file']
            audio_storage_loc = project.find("./audio").attrib['storage_loc']
            firmware_version = project.find("./version").attrib['firmware']
            crop_type = project.find("./origin/metadata").attrib['crop_flag']
            if not crop_type:
                crop_type = "2"

            # update template parameters
            recording_settings["firmware_version"] = firmware_version
            recording_settings["recording_dir"] = os.path.join(recording_settings["source_dir"], recording_name)
            recording_settings["output_destination"] = output_destination
            recording_settings["recording_name"] = recording_name
            recording_settings["trim_start"] = Helpers.parse_int(recording_settings["trim_start"])
            if recording_settings["trim_start"] < 0 or recording_settings["trim_start"] > duration:
                recording_settings["trim_start"] = 0
            else:
                recording_settings["trim_start"] = recording_settings["trim_start"]
            recording_settings["trim_end"] = Helpers.parse_int(recording_settings["trim_end"])
            if recording_settings["trim_end"] < 0:
                recording_settings["trim_end"] = duration + recording_settings["trim_end"]
                if recording_settings["trim_end"] < 0:
                    recording_settings["trim_end"] = duration
            elif 0 < recording_settings["trim_end"] < duration:
                recording_settings["trim_end"] = recording_settings["trim_end"]
            else:
                recording_settings["trim_end"] = duration
            recording_settings["gravity_x"] = gravity_x
            recording_settings["gravity_y"] = gravity_y
            recording_settings["gravity_z"] = gravity_z
            recording_settings["offset_pano"] = offset_pano
            recording_settings["offset_stereo_left"] = offset_stereo_left
            recording_settings["offset_stereo_right"] = offset_stereo_right
            recording_settings["start_ts_1"] = start_ts_1
            recording_settings["start_ts_2"] = start_ts_2
            recording_settings["start_ts_3"] = start_ts_3
            recording_settings["start_ts_4"] = start_ts_4
            recording_settings["start_ts_5"] = start_ts_5
            recording_settings["start_ts_6"] = start_ts_6
            recording_settings["gyro_sweep_time"] = rolling_shutter_time_us
            recording_settings["gyro_delay_time"] = delay_time_us
            recording_settings["source_crop_type"] = crop_type
        except Exception as e:
            raise Exception("Error populating recording parameters from project file: " + str(e))

        try:
            qx, qy, qz, qw = Helpers.euler_degrees_to_quaternion(recording_settings["roll_x"],
                                                                 recording_settings["tilt_y"],
                                                                 recording_settings["pan_z"],
                                                                 y_up=True)
            recording_settings["diff_quat_x"] = qx
            recording_settings["diff_quat_y"] = qy
            recording_settings["diff_quat_z"] = qz
            recording_settings["diff_quat_w"] = qw
        except:
            recording_settings["diff_quat_x"] = 0
            recording_settings["diff_quat_y"] = 0
            recording_settings["diff_quat_z"] = 0
            recording_settings["diff_quat_w"] = 1

        # "blend_mode": "pano",  # Mono: pano, Stereo: stereo_top_left, stereo_top_right, vr180, vr180_4lens
        if recording_settings["blend_mode"] == "vr180":
            recording_settings["blend_lens_selection"] = ProStitcherController.vr180_lens_selection
            recording_settings["blend_vr180_yaw"] = ""
            recording_settings["blend_angle_optical"] = "16"
            recording_settings["output_width"] = str(int(recording_settings["width"]))
            recording_settings["output_height"] = str(int(recording_settings["width"]/2))
        elif recording_settings["blend_mode"] == "vr180_4lens":
            recording_settings["blend_lens_selection"] = "<lensSelection/>"
            recording_settings["blend_vr180_yaw"] = 'vr180Yaw="180"'
            recording_settings["blend_angle_optical"] = "16"
            recording_settings["output_width"] = str(int(recording_settings["width"]))
            recording_settings["output_height"] = str(int(recording_settings["width"]/2))
        elif recording_settings["blend_mode"] in ["stereo_top_left", "stereo_top_right"]:
            recording_settings["blend_lens_selection"] = "<lensSelection/>"
            recording_settings["blend_vr180_yaw"] = ""
            recording_settings["blend_angle_optical"] = "16"
            recording_settings["output_width"] = str(int(recording_settings["width"]))
            recording_settings["output_height"] = str(int(recording_settings["width"]))
        else:
            recording_settings["blend_lens_selection"] = "<lensSelection/>"
            recording_settings["blend_vr180_yaw"] = ""
            recording_settings["blend_angle_optical"] = "20"
            recording_settings["output_width"] = str(int(recording_settings["width"]))
            recording_settings["output_height"] = str(int(recording_settings["width"]/2))

        if recording_settings["stitching_mode"] == "New Optical Flow":
            recording_settings["blend_use_optical_flow"] = "1"
            recording_settings["blend_new_optical_flow"] = "1"
        elif recording_settings["stitching_mode"] == "Optical Flow":
            recording_settings["blend_use_optical_flow"] = "1"
            recording_settings["blend_new_optical_flow"] = "0"
        elif recording_settings["stitching_mode"] == "Scene-specific Template":
            recording_settings["blend_use_optical_flow"] = "0"
            recording_settings["blend_new_optical_flow"] = "0"

        if recording_settings["blend_angle_optical"]:
            try:
                blend_angle_optical = Helpers.parse_float(recording_settings["blend_angle_optical"])
                if blend_angle_optical < 10:
                    recording_settings["blend_angle_optical"] = "10"
                elif blend_angle_optical > 20:
                    recording_settings["blend_angle_optical"] = "20"
                else:
                    recording_settings["blend_angle_template"] = f"{blend_angle_optical}"
            except:
                recording_settings["blend_angle_optical"] = self.default_parameters["blend_angle_optical"]

        if recording_settings["blend_angle_template"]:
            try:
                blend_angle_template = Helpers.parse_float(recording_settings["blend_angle_template"])
                if blend_angle_template < 0.1:
                    recording_settings["blend_angle_template"] = "0.1"
                elif blend_angle_template > 20:
                    recording_settings["blend_angle_template"] = "20"
                else:
                    recording_settings["blend_angle_template"] = f"{blend_angle_template}"
            except:
                recording_settings["blend_angle_template"] = self.default_parameters["blend_angle_template"]

        recording_settings["logo_node"] = ''
        if recording_settings["logo_path"] and str(recording_settings["logo_path"]).lower() != 'none':
            try:
                logo_path = recording_settings["logo_path"]
                logo_angle = Helpers.parse_float(recording_settings["logo_angle"])
                if logo_angle < 1:
                    recording_settings["logo_angle"] = "1"
                elif logo_angle > 60:
                    recording_settings["logo_angle"] = "60"
                else:
                    recording_settings["logo_angle"] = f"{logo_angle}"
                recording_settings["logo_node"] = f'<logo src="{logo_path}" angle="{logo_angle}"/>'
            except:
                recording_settings["logo_node"] = ''

        recording_settings["blend_capture_time"] = Helpers.parse_int(recording_settings["reference_time"])
        if not recording_settings["blend_capture_time"] or recording_settings["blend_capture_time"] > duration or recording_settings["blend_capture_time"] < 0:
            recording_settings["blend_capture_time"] = Helpers.parse_int(duration/2)
        # if recording_settings["output_fps"] == "59.94":
        #     recording_settings["source_crop_type"] = "3"
        # else:
        #     recording_settings["source_crop_type"] = "2"
        recording_settings["gyro_enable"] = "1" if recording_settings["flowstate_stabilisation"] else "0"
        if recording_settings["direction_lock"]:
            recording_settings["gyro_flowstate_mode"] = "2"
        else:
            recording_settings["gyro_flowstate_mode"] = "1"
        recording_settings["blend_smooth_stitch"] = "true" if recording_settings["smooth_stitch"] else "false"
        recording_settings["blend_original_offset"] = "true" if recording_settings["original_offset"] else "false"
        recording_settings["blend_top_fixer"] = "1" if recording_settings["zenith_optimisation"] else "0"
        recording_settings["blender_type"] = recording_settings["blender_type"] or "auto"
        recording_settings["encode_preset"] = recording_settings["encode_preset"] or "superfast"
        recording_settings["encode_profile"] = recording_settings["encode_profile"] or "baseline"
        recording_settings["sampling_level"] = recording_settings["sampling_level"] or "fast"
        recording_settings["encode_use_hardware"] = str(recording_settings["encode_use_hardware"]) or "0"
        recording_settings["decode_hardware_count"] = recording_settings["decode_hardware_count"] or "6"
        recording_settings["decode_use_hardware"] = str(recording_settings["decode_use_hardware"]) or "1"
        recording_settings["output_bitrate"] = str(recording_settings["bitrate"]) or "503316480"
        recording_settings["output_codec"] = recording_settings["output_codec"] or "h264"
        recording_settings["output_format"] = recording_settings["output_format"] or "mp4"

        # audio
        if recording_settings["audio_type"] == "none":
            # no audio
            recording_settings["output_audio_type"] = "none"
        else:
            # default, copy from project settings
            if spatial_audio == "true":
                recording_settings["output_audio_type"] = "pano"
            else:
                recording_settings["output_audio_type"] = "normal"
        recording_settings["output_audio_device"] = audio_device
        recording_settings["audio_file"] = audio_file
        recording_settings["audio_storage_loc"] = audio_storage_loc

        # fps & interpolation
        recording_settings["output_fps"] = str(recording_settings["output_fps"]) or "29.97"
        if recording_settings["output_fps"] == "default":
            recording_settings["output_fps"] = Helpers.parse_float(input_fps)
            recording_settings["output_interpolation"] = "0"
        else:
            input_fps = Helpers.parse_float(input_fps)
            recording_settings["output_fps"] = Helpers.parse_float(recording_settings["output_fps"])
            recording_settings["output_interpolation"] = "0"

            # determine interpolation settings. Turning interpolation on doubles the specified frame rate.
            if recording_settings["output_fps"] == 2 * input_fps:
                recording_settings["output_fps"] = input_fps
                recording_settings["output_interpolation"] = "1"
            else:
                recording_settings["output_interpolation"] = "0"

        # color
        recording_settings["color_brightness"] = recording_settings["brightness"] or "0"
        recording_settings["color_contrast"] = recording_settings["contrast"] or "0"
        recording_settings["color_highlight"] = recording_settings["highlight"] or "0"
        recording_settings["color_shadow"] = recording_settings["shadow"] or "0"
        recording_settings["color_saturation"] = recording_settings["saturation"] or "0"
        recording_settings["color_temperature"] = recording_settings["temperature"] or "0"
        recording_settings["color_tint"] = recording_settings["tint"] or "0"
        recording_settings["color_sharpness"] = recording_settings["sharpness"] or "0"

        # fix known settings constraints
        if sys.platform == "darwin" and recording_settings["blender_type"] == "cuda":
            # cuda not supported on mac
            recording_settings["blender_type"] = "opencl"
        if recording_settings["output_codec"] == "prores":
            # prores only supports encode_profile=3
            recording_settings["encode_profile"] = "3"
            # prores only supports output_format=mov
            recording_settings["output_format"] = "mov"
        elif recording_settings["output_codec"] == "h265" and recording_settings["encode_profile"] == "baseline":
            # h265 encoding crashes with encode_profile=baseline. Set encode_profile=main
            recording_settings["encode_profile"] = "main"

        # replace parameters in template
        recording_template = ProStitcherController.stitcher_template
        for k, v in recording_settings.items():
            recording_template = recording_template.replace("${}".format(k.upper()), str(v))

        # remove destination file if exists
        try:
            if os.path.exists(recording_settings["output_destination"]):
                os.remove(recording_settings["output_destination"])
        except:
            pass

        return recording_template

    def process_recording(self, recording):
        result = -1
        t = strftime("%H%M%S", localtime())

        # make private copy as we'll change some things for each recording
        recording_settings = copy.deepcopy(self.settings)

        # insert any default settings not present
        for k,v in self.default_parameters.items():
            if k not in recording_settings:
                recording_settings[k] = v

        preview_filepath = os.path.join(recording_settings["source_dir"], recording, "preview.mp4")
        duration, fps = self._run_ffprobe(recording_settings["ffprobe_path"], preview_filepath)
        if duration >= recording_settings["min_recording_duration"]:

            # create file paths
            tempdir = tempfile.gettempdir()
            recording_project_file = os.path.join(recording_settings["source_dir"], recording, "pro.prj")
            destination_file = "{}_{}.{}".format(recording, t, recording_settings["output_format"])
            output_destination = os.path.join(recording_settings["target_dir"], destination_file)
            project_filepath = os.path.join(tempdir, recording + "_{}_project.xml".format(t))
            template_filepath = os.path.join(tempdir, recording + "_{}_template.xml".format(t))
            recording_logfile = os.path.join(tempdir, recording + "_{}_stitcher.log".format(t))
            parameters_filepath = os.path.join(tempdir, recording + "_{}_parameters.json".format(t))

            # update trim settings from relative to absolute.
            if recording_settings["trim_start"] < 0 or recording_settings["trim_start"] > duration:
                recording_settings["trim_start"] = 0
            if recording_settings["trim_end"] < 0:
                recording_settings["trim_end"] = duration + recording_settings["trim_end"]
                if recording_settings["trim_end"] < 0:
                    recording_settings["trim_end"] = duration
            # calculate total stitching duration
            stitching_duration = recording_settings["trim_end"] - recording_settings["trim_start"]

            if stitching_duration <= 0:
                self._log_error(
                    "ERROR: Stitching duration for {} is {}s. Please check your settings for 'Trim start' and 'Trim end'.".format(
                        recording, stitching_duration))
                return result

            # read project file
            if os.path.exists(recording_project_file):
                recording_project_data = Helpers.read_file(recording_project_file)
                Helpers.write_file(project_filepath, recording_project_data)

                # get stitcher version
                # stitcher_major_version = ProStitcherController.get_prostitcher_major_version(recording_settings['stitcher_path'])

                # create stitching template for this recording
                recording_template = self.update_template(recording_settings,
                                                            recording,
                                                            int(duration),
                                                            fps,
                                                            recording_project_data,
                                                            output_destination)
                Helpers.write_file(template_filepath, recording_template)
                try:
                    Helpers.write_file(parameters_filepath, json.dumps(recording_settings, indent=4))
                except:
                    pass

                # stitch
                stitching_duration = int(stitching_duration)
                self._log_info("\nStitching {} (duration: {}s) ".format(recording, stitching_duration))
                self._log_info(f"ProStitcher: {recording_settings['stitcher_path']}\n"
                                f"Template: {os.path.abspath(template_filepath)}\n"
                                f"Logfile: {os.path.abspath(recording_logfile)}\n"
                                f"Settings: {os.path.abspath(parameters_filepath)}")
                if not self._stopping:
                    t1 = time()
                    result = self._run_prostitcher(recording_settings["stitcher_path"],
                                         tempdir,
                                         os.path.abspath(template_filepath),
                                         os.path.abspath(recording_logfile),
                                         os.path.abspath(parameters_filepath))
                    if result == 0:
                        t2 = time()
                        t3 = int(t2 - t1)
                        self._log_info("Completed {} in {}s at {} fps.".format(recording, t3,
                                                                             round(float(fps) * int(stitching_duration) / t3, 2)))

                        if recording_settings["rename_after_stitching"]:
                            try:
                                cur_path = os.path.join(recording_settings["source_dir"], recording)
                                new_path = os.path.join(recording_settings["source_dir"], recording_settings["rename_prefix"] + recording)
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
        self.settings["decode_hardware_count"] = Helpers.parse_int(self.settings["decode_hardware_count"])
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
