#!/usr/bin/python3
# -*- coding: utf-8 -*-

__author__ = "Axel Busch"
__copyright__ = "Copyright 2022, Xlvisuals Limited"
__license__ = "GPL-2.1"
__version__ = "0.0.6"
__email__ = "info@xlvisuals.com"

import sys
import shutil
import copy
import pathlib
import string
import os.path
import configparser
from os import scandir
from math import sin, cos, degrees, atan2, asin, pi


class Helpers:

    @staticmethod
    def get_datadir():
        home = pathlib.Path.home()

        if sys.platform == "win32":
            if os.getenv('APPDATA'):
                return os.path.abspath(os.getenv('APPDATA'))
            else:
                return os.path.abspath(os.path.join(home, "AppData/Roaming"))
        elif sys.platform == "darwin":
            return os.path.abspath(os.path.join(home, "Library/Application Support"))
        elif sys.platform.startswith("linux"):
            return os.path.abspath(os.path.join(home, ".local/share"))
        else:
            return home

    @staticmethod
    def get_free_space(folder):
        total, used, free = shutil.disk_usage(folder)
        return free

    @staticmethod
    def get_used_space(folders=(), whole_disk=False):
        total_used = 0
        for f in folders:
            if whole_disk:
                total, used, free = shutil.disk_usage(f)
                total_used += used
            else:
                for path, dirs, files in os.walk(f):
                    for f in files:
                        fp = os.path.join(path, f)
                        total_used += os.path.getsize(fp)
        return total_used

    @staticmethod
    def get_drives():
        drives = []
        if sys.platform == "win32":
            from ctypes import windll
            bitmask = windll.kernel32.GetLogicalDrives()
            for letter in string.ascii_uppercase:
                if bitmask & 1:
                    drives.append(letter + ':')
                bitmask >>= 1
        elif sys.platform == "darwin":
            subdirs = Helpers.get_subdirs("/Volumes")
            for subdir in subdirs:
                drives.append(os.path.join("/Volumes", subdir))
        elif sys.platform == "linux":
            subdirs = Helpers.get_subdirs("/media")
            for subdir in subdirs:
                drives.append(os.path.join("/media", subdir))
        return drives

    @staticmethod
    def get_subdirs(path, startswith=None, sort=True):
        result = []
        if os.path.isdir(path):
            for entry in scandir(path):
                if entry.is_dir():
                    if startswith:
                        if entry.name.startswith(startswith):
                            result.append(entry.name)
                    else:
                        result.append(entry.name)
        if sort:
            return sorted(result)
        else:
            return result

    @staticmethod
    def parse_int(value, default=0):
        try:
            value = int(value)
        except (ValueError, TypeError):
            value = default
        return value

    @staticmethod
    def parse_bool(value, default=False):
        """
        Returns True if value is True, a positive number, or equals "yes", "true", "on", "y".
        Returns False if value is False, 0, negative, or any other string.
        """
        try:
            if value == True:
                return True
            elif str(value).lower() in ["yes", "true", "on", "y", "1"]:
                return True
            elif Helpers.parse_int(value) <= 0:
                return False
            else:
                return bool(value)
        except (ValueError, TypeError):
            return default

    @staticmethod
    def parse_float(value, default=0.0, precision=8):
        try:
            if type(value) is str:
                dot_pos = value.find(".")
                comma_pos = value.find(",")
                if dot_pos >= 0 and 0 <= comma_pos < dot_pos:
                    # remove thousands comma separator
                    value = value.replace(',', '')
                elif 0 <= dot_pos < comma_pos and comma_pos >= 0:
                    # remove thousands dot separator and fix decimal comma separator
                    value = value.replace('.', '')
                    value = value.replace(',', '.')
                elif comma_pos >= 0:
                    # remove thousands comma separator
                    value = value.replace(',', '.')
            if not precision:
                value = float(value)
            else:
                value = round(float(value), precision)
        except:
            value = default
        return value

    @staticmethod
    def read_file(filename, encoding='utf-8', binary=False, default=''):
        try:
            data = None
            if binary:
                with open(filename, 'rb') as fd:
                    data = fd.read()
            else:
                with open(filename, 'r', encoding=encoding) as fd:
                    data = fd.read()
            return data
        except Exception as e:
            sys.stderr.write("Error reading file: {}".format(str(e)))
        return default

    @staticmethod
    def write_file(filename, data, encoding='utf-8', binary=False):
        try:
            if binary:
                with open(filename, 'wb') as fd:
                    fd.write(data)
            else:
                with open(filename, 'w', encoding=encoding) as fd:
                    fd.write(data)
            return len(data)
        except Exception as e:
            sys.stderr.write("Error writing file: {}".format(str(e)))
        return 0

    @staticmethod
    def euler_degrees_to_quaternion(roll_x, pitch_y, yaw_z, y_up=False):
        if y_up:
            temp = pitch_y
            pitch_y = yaw_z
            yaw_z = temp
        roll_x = Helpers.parse_float(roll_x) * pi / 180
        pitch_y = Helpers.parse_float(pitch_y) * pi / 180
        yaw_z = Helpers.parse_float(yaw_z) * pi / 180
        qx = Helpers.parse_float(
            sin(roll_x / 2) * cos(pitch_y / 2) * cos(yaw_z / 2) - cos(roll_x / 2) * sin(pitch_y / 2) * sin(yaw_z / 2))
        qy = Helpers.parse_float(
            cos(roll_x / 2) * sin(pitch_y / 2) * cos(yaw_z / 2) + sin(roll_x / 2) * cos(pitch_y / 2) * sin(yaw_z / 2))
        qz = Helpers.parse_float(
            cos(roll_x / 2) * cos(pitch_y / 2) * sin(yaw_z / 2) - sin(roll_x / 2) * sin(pitch_y / 2) * cos(yaw_z / 2))
        qw = Helpers.parse_float(
            cos(roll_x / 2) * cos(pitch_y / 2) * cos(yaw_z / 2) + sin(roll_x / 2) * sin(pitch_y / 2) * sin(yaw_z / 2))
        return qx, qy, qz, qw

    @staticmethod
    def quaternion_to_euler_degrees(qx, qy, qz, qw):
        qx = Helpers.parse_float(qx)
        qy = Helpers.parse_float(qy)
        qz = Helpers.parse_float(qz)
        qw = Helpers.parse_float(qw)
        ysqr = qy * qy

        t0 = +2.0 * (qw * qx + qy * qz)
        t1 = +1.0 - 2.0 * (qx * qx + ysqr)
        roll_x = degrees(atan2(t0, t1))

        t2 = +2.0 * (qw * qy - qz * qx)
        t2 = +1.0 if t2 > +1.0 else t2
        t2 = -1.0 if t2 < -1.0 else t2
        pitch_y = degrees(asin(t2))

        t3 = +2.0 * (qw * qz + qx * qy)
        t4 = +1.0 - 2.0 * (ysqr + qz * qz)
        yaw_z = degrees(atan2(t3, t4))

        return roll_x, pitch_y, yaw_z

    @staticmethod
    def read_config(config_file, default_settings, section="DEFAULT"):
        """
        Reads settings from config file, or sets to default settings
        :return: dictionary with settings
        """
        # populate with default values
        config_settings = copy.deepcopy(default_settings)
        try:
            config = configparser.ConfigParser()
            if os.path.isfile(config_file):
                try:
                    config.read(config_file)
                except configparser.MissingSectionHeaderError as e:
                    with open(config_file) as stream:
                        config.read_string(f'[{section}]\n' + stream.read())

                # copy values from settings
                for key, v in config[section].items():
                    if key not in default_settings:
                        config_settings[key] = v
                    else:
                        # convert to same type as in default settings
                        try:
                            if type(default_settings[key]) is str:
                                config_settings[key] = str(v)
                            elif type(default_settings[key]) is int:
                                config_settings[key] = Helpers.parse_int(v)
                            elif type(default_settings[key]) is bool:
                                config_settings[key] = Helpers.parse_bool(v)
                            elif type(default_settings[key]) is float:
                                config_settings[key] = Helpers.parse_float(v)
                            else:
                                config_settings[key] = v
                        except Exception as e:
                            print("Error setting ini file parameter {}: {}".format(key, e))
            else:
                print(f"File not found: {config_file}")
        except Exception as e:
            print("Error reading config file: {}".format(str(e)))
        return config_settings

    @staticmethod
    def write_config(config_file, settings, section="DEFAULT"):
        try:
            config = configparser.ConfigParser()
            config[section] = {}
            if not settings:
                settings = {}
            for key in settings.keys():
                if settings.get(key) is not None:
                    config[section][key] = str(settings.get(key))
                else:
                    config[section][key] = ''
            with open(config_file, "w") as file:
                config.write(file)
                file.close()
            return True
        except Exception as e:
            print("Error writing config file: {}".format(str(e)))
            return False

