
# Batch Stitcher for Insta360 Pro 2

## Introduction

This is a Python3 program to stitch multiple Insta360 Pro 2 recordings from a common source folder with the same settings.


## Requirements

Batchstitcher is pure Python 3 code (>= Python 3.8) and does not require external libraries or compilation. 

However, if you're on macOS you might have to install python-tk along with your Python 3 installation.

```
brew install python@3.10
brew install python-tk@3.10
```

The stitching process relies on two external programs:
- **ProStitcher**, which is part of the Insta360Stitcher application.
  - Download: https://www.insta360.com/download/insta360-pro2
  - Insta360 can provide optimized versions for RTX30xx and Apple Silicon on request.
- **ffprobe**, which is part of the free FFmpeg video utilities. 
  - Download: https://ffmpeg.org/download.html


## Usage

Start batchsticher.py from the command line.

```
python3 batchsticher.py
```

![alt text](./batchstitcher.png)

At a minimum you must enter the following settings:

- Source folder: The folder which contains the VID_xxx_xxx project files
- Target folder: The folder where the program should save the stitched video files
- ProStitcher executable: Choose your Insta360Stitcher installation.
  - Default for Windows: C:/Program Files (x86)/Insta360Stitcher/tools/prostitcher/ProStitcher.exe
  - Default for macOS: /Applications/Insta360Stitcher.app/Contents/Resources/tools/ProStitcher/ProStitcher
  - You may select the Insta360Stitcher folder or the ProStitcher binary
  - Insta360 can provide optimized versions for RTX30xx and Apple Silicon
 
The other parameters should be familiar from the Insta360Stitcher UI. 

Some options are named slightly differntly (e.g. pano instead of Monoscopic). 
This is because the ProStitcher executable uses different configuration strings than the Insta360Stitcher UI. 

The following two settings are of special importance: 

- Blender type:
  - Blender type selects the stitching backend (library).
  - Four options are available but it depends on your hardware which is supported.
    - "auto" lets ProStitcher choose wich backend to use. Not recommended.
    - "cuda" is the fastest backend, but only available with NVidia GTX/RTX GPUs and a compatible Insta360Stitcher version
    - "opencl" is the 2nd fastest and available with all most GPUs on all platforms.
    - "cpu" is the slowest and available on all platforms.
  - If you choose a blender type that's not supported by your hardware, ProStitcher might not show an error and fall back to 'cpu' mode, which is very slow. 
  - It is recommended to try "opencl" and compare with your default settings to see which one is faster.

- Use hardware encoding: 
  - If you activate "Use hardware encoding" in the output section, and the encoding settings is not supported by your hardware, you'll see an error message in the progress window that says so (return code 244 - hardware encoding not supported). 
  - In this case please deactivate "Use hardware encoding" and try again.

## Problem resolution

- The progress window should provide enough information if something goes wrong. 
- The progress window also shows the paths to the stitcher logfile for each stitch that fails.
- The progress window shows the achieved stitching frame rate (fps) at the end of the stitching process. If that is below 1 fps it is likely that ProStitcher is using "cpu" blender type. Please check if "opencl" provides a faster stitch.