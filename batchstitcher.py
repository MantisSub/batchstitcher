#!/usr/bin/python3
# -*- coding: utf-8 -*-
"""
Stitch multiple VID_xxx recording projects captured with Insta360 Pro 2
"""

__author__ = "Axel Busch"
__copyright__ = "Copyright 2023, Xlvisuals Limited"
__license__ = "GPL-2.1"
__version__ = "0.0.7"
__email__ = "info@xlvisuals.com"

import shutil
import sys
import os.path
import copy
import threading
from sys import platform
import tkinter as tk
from tkinter import ttk
from tkinter import filedialog, messagebox, scrolledtext
from helpers import Helpers
from prostitchercontroller import ProStitcherController
from time import sleep


class BatchStitcher():

    def __init__(self):
        self.inifile_name = "batchstitcher.ini"
        self.inifile_path = None
        self.root = None
        self.style = None
        self.settings = {}
        self.settings_stringvars = {}
        self.settings_intvars = {}
        self.settings_widgets = {}
        self.settings_labels = {}
        self.settings_buttons = {}
        self.button_cancel = None
        self.button_start = None
        self.text_area = None
        self.line_length = 0
        self.max_line_length = 100

        self.themes_path = os.path.abspath('awthemes-10.4.0')
        self.theme_names = ['awdark', 'awlight']
        self.iconbitmap = None
        self.editor_width = 50
        self.button_width = 20
        self.scroll_width = 780
        self.scroll_height = 400
        self.intvar_keys = ["original_offset", "decode_use_hardware", "decode_hardware_count", "encode_use_hardware", "zenith_optimisation", "flowstate_stabilisation", "direction_lock", "smooth_stitch", "rename_after_stitching"]

        self._stitcher = None
        self._stitching_thread = None
        self._lock = threading.Lock()
        self._unprocessed_logs = []
        self._can_quit = True

        if platform == "darwin":
            self.default_stitcher_subdir = ProStitcherController.DEFAULT_STITCHER_SUBDIR_MAC
        else:
            self.default_stitcher_subdir = ProStitcherController.DEFAULT_STITCHER_SUBDIR_WIN

    def init(self):
        # Read ini file

        # Scripts running under py2exe do not have a __file__ global
        default_inifile_path = os.path.join(os.path.dirname(os.path.realpath(sys.argv[0])), self.inifile_name)
        if not os.path.exists(default_inifile_path):
            default_inifile_path = self.inifile_name
        try:
            inifile_dir = os.path.join(Helpers.get_datadir(), "BatchStitcher")
            self.inifile_path = os.path.join(inifile_dir, self.inifile_name)

            if not os.path.exists(inifile_dir):
                try:
                    os.mkdir(inifile_dir)
                except Exception as e:
                    print("Could not create data dir: ", e)
            if not os.path.exists(self.inifile_path):
                shutil.copy(default_inifile_path, self.inifile_path)
        except:
            if not self.inifile_path:
                self.inifile_path = default_inifile_path

        self.settings = Helpers.read_config(self.inifile_path, ProStitcherController.default_settings)
        if self.settings and platform == "darwin" and self.settings.get("blender_type") == "cuda":
            self.settings["blender_type"] = "opencl"

        # Check for executables
        if not self.settings["ffprobe_path"]:
            if platform == "darwin" and os.path.exists(ProStitcherController.DEFAULT_STITCHER_MAC):
                self.settings["ffprobe_path"] = ProStitcherController.DEFAULT_FFPROBE_MAC
            elif os.path.exists(ProStitcherController.DEFAULT_FFPROBE_WIN):
                self.settings["ffprobe_path"] = ProStitcherController.DEFAULT_FFPROBE_WIN
        else:
            if platform != "darwin" and not self.settings["ffprobe_path"].endswith(".exe"):
                self.settings["ffprobe_path"] += ".exe"

        if not self.settings["stitcher_path"]:
            if platform == "darwin" and os.path.exists(ProStitcherController.DEFAULT_STITCHER_MAC):
                self.settings["stitcher_path"] = ProStitcherController.DEFAULT_STITCHER_MAC
            elif os.path.exists(ProStitcherController.DEFAULT_STITCHER_WIN):
                self.settings["stitcher_path"] = ProStitcherController.DEFAULT_STITCHER_WIN

        # Perform sanity checks
        if not self.settings["stitcher_path"] or not os.path.isfile(self.settings["stitcher_path"]):
            self.settings["stitcher_path"] = ""
        if not self.settings["source_dir"] or not os.path.isdir(self.settings["source_dir"]):
            self.settings["source_dir"] = ""
        if not self.settings["target_dir"] or not os.path.isdir(self.settings["target_dir"]):
            if self.settings["source_dir"] and not self.settings["target_dir"]:
                self.settings["target_dir"] = self.settings["source_dir"]
            else:
                self.settings["target_dir"] = ""
        if self.settings.get("audio_type") and self.settings.get("audio_type") != "none":
            self.settings["audio_type"] = "default"

        self._init_gui()

    def _init_gui(self):
        self._init_tk()
        self._init_ttk()
        for k in self.settings.keys():
            self.settings_stringvars[k] = tk.StringVar(value=str(self.settings[k]))
            self.settings_widgets[k] = None
            self.settings_labels[k] = None
            self.settings_buttons[k] = None
        for k in self.intvar_keys:
            self.settings_intvars[k] = tk.IntVar(value=Helpers.parse_int(self.settings[k]))
        self.settings_intvars["bitrate_mbps"] = tk.IntVar(value=int(Helpers.parse_int(self.settings["bitrate"])/1024/1024))

        if platform == "darwin":
            self.editor_width = 25
            self.button_width = 10


    def _init_tk(self):
        # Create root element and load and set theme
        self.root = tk.Tk()
        self.root.title("Batch Stitcher")
        self.root.columnconfigure(0, minsize=150)
        self.root.columnconfigure(1, minsize=300)
        self.root.columnconfigure(2, minsize=155)
        self.root.rowconfigure(0, weight=1)
        if self.iconbitmap and os.path.isfile(self.iconbitmap):
            self.root.iconbitmap(self.iconbitmap)
        self.root.resizable(False, False)

        menubar = tk.Menu(self.root)
        filemenu = tk.Menu(menubar, tearoff=False)
        filemenu.add_command(label="About ...", command=self._on_about)
        filemenu.add_separator()
        filemenu.add_command(label="Exit", command=self._on_quit)
        menubar.add_cascade(label="File", menu=filemenu)
        self.root.config(menu=menubar)

        self.root.bind("<<log_callback>>", self._on_log_callback)
        self.root.bind("<<done_callback>>", self._on_done_callback)

    def _init_ttk(self):
        # Load and set theme
        if not self.root:
            self._init_tk()
        if self.root:
            self.root.tk.call('lappend', 'auto_path', self.themes_path)
            try:
                for name in self.theme_names:
                    self.root.tk.call('package', 'require', name)
                self.style = ttk.Style(self.root)
                self.style.theme_use(self.theme_names[0])
            except Exception as e:
                print("Error setting up tk themes: ", e)
                self.style = None

    def _on_mousewheel(self, event):
        self.scroll_canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        # if event.state == 0:
        #     self.scroll_canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        # else:
        #     self.scroll_canvas.xview_scroll(int(-1 * (event.delta / 120)), "units")
        return "break"

    def _on_touchpad(self, event):
        if event.num == 6:
            self.scroll_canvas.xview_scroll(int(-1 * (event.delta / 120)), "units")
            return "break"
        elif event.num == 7:
            self.scroll_canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
            return "break"

    def _create_scroll_frame(self, row):
        # Because there are a lot of settings, we put them into section that can scroll.
        self.parent_frame = tk.Frame(self.root)
        self.parent_frame.grid(row=row, column=0, columnspan=4, padx=50, pady=0, sticky='nw')
        self.parent_frame.grid_rowconfigure(0, minsize=self.scroll_height, weight=1)
        self.parent_frame.grid_columnconfigure(0, minsize=self.scroll_width, weight=1)
        # Set grid_propagate False to allow resizing later
        self.parent_frame.grid_propagate(False)

        # Add a canvas in that frame, which comes with scrolling feature
        self.scroll_canvas = tk.Canvas(self.parent_frame)
        self.scroll_canvas.grid(row=0, column=0, padx=0, pady=0, sticky="news")
        self.scrollcanvas_vsb = ttk.Scrollbar(self.parent_frame, orient="vertical", command=self.scroll_canvas.yview)
        self.scrollcanvas_vsb.grid(row=0, column=1, sticky='ns', padx=0, pady=5)
        self.scroll_canvas.configure(yscrollcommand=self.scrollcanvas_vsb.set)
        self.scroll_canvas.bind_all("<MouseWheel>", self._on_mousewheel)

        # Create a frame to contain our scrollable content and attach it to the canvas
        self.scroll_frame = tk.Frame(self.scroll_canvas, padx=0, pady=0, borderwidth=2, relief='sunken')
        self.scroll_frame.columnconfigure(0, minsize=200)
        self.scroll_frame.columnconfigure(1, minsize=200)
        self.scroll_frame.columnconfigure(2, minsize=400)
        self.scroll_frame.grid_rowconfigure(0, weight=1)
        self.scroll_canvas.create_window((0, 0), window=self.scroll_frame, anchor='nw')

    def _resize_scroll_frame(self, width, height):
        self.scroll_frame.update_idletasks()
        self.parent_frame.config(width=width + self.scrollcanvas_vsb.winfo_width(), height=height)
        self.scroll_canvas.config(scrollregion=self.scroll_canvas.bbox("all"))

    def set_theme(self, index):
        if index >= len(self.theme_names):
            index = 0
        if self.style:
            self.style.theme_use(self.theme_names[index])
            self.root.configure(bg=self.style.lookup('TFrame', 'background'))
            self.parent_frame.configure(bg=self.style.lookup('TFrame', 'background') or 'grey')
            self.scroll_canvas.configure(bg=self.style.lookup('TFrame', 'background') or 'grey')
            self.scroll_frame.configure(bg=self.style.lookup('TFrame', 'background') or 'grey')
        else:
            self.root.configure(bg='grey')
            self.parent_frame.configure(bg='grey')
            self.scroll_canvas.configure(bg='grey')
            self.scroll_frame.configure(bg='grey')

    def toggle_theme(self):
        try:
            cur_index = self.theme_names.index(self.style.theme_use())
        except:
            cur_index = 0
        self.set_theme(cur_index+1)

    def _on_select_source_dir(self):
        idir = self.settings_stringvars["source_dir"].get() or None
        fdir = filedialog.askdirectory(initialdir=idir)
        if fdir:
            self.settings_stringvars["source_dir"].set(fdir)
            self.settings_widgets["source_dir"].delete(0, tk.END)  # deletes the current value
            self.settings_widgets["source_dir"].insert(0, fdir)  # inserts new value assigned by 2nd parameter

        if not os.path.isdir(self.settings_stringvars["source_dir"].get()):
            messagebox.showwarning(title="Warning", message="No valid source folder selected.")
        else:
            recordings = Helpers.get_subdirs(self.settings_stringvars["source_dir"].get(), self.settings["source_filter"])
            if not recordings:
                messagebox.showwarning(title="Warning", message="No VID_xxx_xxx subdirectories found.")

    def _on_select_target_dir(self):
        idir = self.settings_stringvars["target_dir"].get() or None
        fdir = filedialog.askdirectory(initialdir=idir)
        if fdir:
            self.settings_stringvars["target_dir"].set(fdir)
            self.settings_widgets["target_dir"].delete(0, tk.END)  # deletes the current value
            self.settings_widgets["target_dir"].insert(0, fdir)  # inserts new value assigned by 2nd parameter
        if not os.path.isdir(self.settings_stringvars["target_dir"].get()):
            messagebox.showwarning(title="Warning", message="No valid target folder selected.")

    def _on_select_prostitcher(self):
        ifile = self.settings_stringvars["stitcher_path"].get() or None
        if ifile:
            idir = os.path.dirname(ifile)
        else:
            idir = None

        if platform == "darwin":
            filetypes = []
        else:
            filetypes = [("ProStitcher", "ProStitcher.exe"), ]

        ffile = filedialog.askopenfilename(initialfile=ifile,
                                           initialdir=idir,
                                           filetypes=filetypes,
                                           title="Please select the ProStitcher executable")

        is_valid = False
        if os.path.isfile(ffile):
            is_valid = True
        elif os.path.isfile(os.path.join(ffile, self.default_stitcher_subdir)):
            ffile = os.path.join(ffile, self.default_stitcher_subdir)
            is_valid = True

        if ffile:
            self.settings_stringvars["stitcher_path"].set(ffile)
            self.settings_widgets["stitcher_path"].delete(0, tk.END)
            self.settings_widgets["stitcher_path"].insert(0, ffile)
        if not is_valid:
            messagebox.showwarning(title="Warning", message="No ProStitcher executable selected.")

    def _on_select_ffprobe(self):
        ifile = self.settings_stringvars["ffprobe_path"].get() or None
        if ifile:
            idir = os.path.dirname(ifile)
        else:
            idir = None

        if platform == "darwin":
            filetypes = []
        else:
            filetypes = [("ffprobe", "ffprobe.exe"), ]

        ffile = filedialog.askopenfilename(initialfile=ifile,
                                           initialdir=idir,
                                           filetypes=filetypes,
                                           title="Please select the ffprobe executable")
        if ffile:
            self.settings_stringvars["ffprobe_path"].set(ffile)
            self.settings_widgets["ffprobe_path"].delete(0, tk.END)
            self.settings_widgets["ffprobe_path"].insert(0, ffile)
        if not os.path.isfile(ffile):
            messagebox.showwarning(title="Warning", message="No ffprobe executable selected.")

    def _on_cancel(self):
        if self._stitcher:
            self._stitcher.stop()

    def _on_about(self):
        title = 'About Batch Stitcher'
        message = (
            'Batch Stitcher for Insta360 Pro 2 by Axel Busch\n'
            'Version ' + __version__ + '\n'
            '\n'
            'Provided by Mantis Sub underwater housing for Pro 2\n'
            'Visit https://www.mantis-sub.com/'
        )
        disclaimer = (
            'This program is distributed in the hope that it will be useful, '
            'but WITHOUT ANY WARRANTY; without even the implied warranty of '
            'MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU '
            'Lesser General Public License for more details.'
        )
        messagebox.showinfo(title=title, message=message, detail=disclaimer)

    def _on_quit(self):
        self._on_cancel()
        while not self._can_quit:
            self.root.update_idletasks()
            self.root.update()
            sleep(0.1)
        self.root.quit()

    def _on_save(self, to_file=False, quiet=False):
        result = True
        for k in self.settings_stringvars.keys():
            try:
                self.settings[k] = self.settings_stringvars[k].get()
            except Exception as e:
                if not quiet:
                    messagebox.showwarning(title="Warning", message=f"Could not save setting {k}: {str(e)}")
                else:
                    print(f"Could not save setting {k}: {str(e)}")
        for k in self.intvar_keys:
            try:
                self.settings[k] = self.settings_intvars[k].get()
            except Exception as e:
                if not quiet:
                    messagebox.showwarning(title="Warning", message=f"Could not save setting {k}: {str(e)}")
                else:
                    print(f"Could not save setting {k}:: {str(e)}")
        if self.settings_intvars.get("bitrate_mbps"):
            try:
                self.settings["bitrate"] = Helpers.parse_int(self.settings_intvars["bitrate_mbps"].get()) * 1024 * 1024
            except Exception as e:
                if not quiet:
                    messagebox.showwarning(title="Warning", message=f"Could not save setting bitrate_mbps: {str(e)}")
                else:
                    print(f"Could not save setting bitrate_mbps: {str(e)}")

        if to_file:
            # optional
            # We do this so next time the same settings are loaded as default. No important for next processing step.
            try:
                if Helpers.write_config(self.inifile_path, self.settings):
                    self.log("Settings saved to file.")
                else:
                    self.log("Could not save settings to file.")
            except Exception as e:
                self.log(f"Error saving settings to file: {str(e)}")

        return result

    def _clear_log(self):
        self.text_area.configure(state=tk.NORMAL)
        self.text_area.delete('1.0', tk.END)
        self.text_area.configure(state=tk.DISABLED)

    def _on_start(self):

        def start_stitcher():
            self._stitcher = ProStitcherController()
            self._stitcher.settings = copy.deepcopy(self.settings)
            self._stitcher.stitch(self.log_callback, self.done_callback)

        try:
            self._clear_log()
            self.button_start.config(state=tk.DISABLED)
            self.button_cancel.config(state=tk.NORMAL)
            self._on_save(to_file=True, quiet=True)

            if not os.path.isdir(self.settings.get('source_dir')):
                messagebox.showwarning(title="Warning", message="No valid source folder selected.")
            elif not os.path.isdir(self.settings.get('target_dir')):
                messagebox.showwarning(title="Warning", message="No valid target folder selected.")
            elif not os.path.isfile(self.settings.get('stitcher_path')):
                messagebox.showwarning(title="Warning", message="No ProStitcher executable selected.")
            elif not os.path.isfile(self.settings.get('ffprobe_path')):
                messagebox.showwarning(title="Warning", message="No ffprobe executable selected.")
            else:
                self._stitching_thread = threading.Thread(target=start_stitcher)
                if self._stitching_thread:
                    self._stitching_thread.start()
                    self._can_quit = False
        finally:
            if not self._is_stitching_thread_alive():
                self._stitcher = None
                self.button_start.config(state=tk.NORMAL)
                self.button_cancel.config(state=tk.DISABLED)

    def _is_stitching_thread_alive(self):
        alive = False
        if self._stitching_thread:
            alive = self._stitching_thread.is_alive()
            if not alive:
                self._stitching_thread.join(2)
                self._stitching_thread = None
        return alive

    def log(self, text):
        # Only call from main gui thread
        if text:
            try:
                if self.text_area:
                    self.text_area.configure(state=tk.NORMAL)
                    if text != "." or self.line_length > self.max_line_length:
                        self.text_area.insert(tk.END, "\n")
                        self.line_length = 0
                    self.text_area.insert(tk.END, text)
                    self.line_length += len(text)
                    self.text_area.configure(state=tk.DISABLED)
                    self.text_area.see(tk.END)  # Scroll to end
            except Exception as e:
                print("Error in log(): ", str(e))
                print(text)

    def log_callback(self, level, text):
        try:
            # It's not safe to call tkinter directly from a different thread.
            # But we can send store the data temporarily and send a message to tkinter to process it.
            try:
                self._lock.acquire()
                self._unprocessed_logs.append(text)
            finally:
                self._lock.release()
            self.root.event_generate("<<log_callback>>")
        except Exception as e:
            print(f"Error logging {level} {text}: {str(e)}", )

    def _on_log_callback(self, event=None):
        if self.text_area:
            try:
                self._lock.acquire()
                for text in self._unprocessed_logs:
                    self.log(text)
                self._unprocessed_logs.clear()
            finally:
                self._lock.release()

    def done_callback(self):
        self.root.event_generate("<<done_callback>>")

    def _on_done_callback(self, event=None):
        if self._is_stitching_thread_alive():
            self.root.update_idletasks()
            self.root.update()
            sleep(0.1)
        if self._stitching_thread:
            self._stitching_thread.join(1)
            self._stitching_thread = None
        self._stitcher = None
        self._can_quit = True
        if self.button_start:
            self.button_start.config(state=tk.NORMAL)
            self.button_cancel.config(state=tk.DISABLED)

    def _populate_scroll_frame(self):

        row_s = 0
        ttk.Label(self.scroll_frame, text="Setup", anchor='se', font=('Arial',16, 'underline')).grid(row=row_s, column=0,padx=2, pady=12,sticky="e")

        settings_with_buttons = [("source_dir", 'Source folder:',self._on_select_source_dir),
                                 ("target_dir", 'Output folder:', self._on_select_target_dir),
                                 ("stitcher_path", 'ProStitcher executable:', self._on_select_prostitcher),
                                 ("ffprobe_path", 'FFprobe executable:', self._on_select_ffprobe)]
        for swb in settings_with_buttons:
            row_s += 1
            k = swb[0]
            self.settings_labels[k] = ttk.Label(self.scroll_frame, text=swb[1], anchor='e', width=25)
            self.settings_labels[k].grid(row=row_s, column=0, padx=2, pady=2, sticky="e")
            self.settings_widgets[k] = ttk.Entry(self.scroll_frame, textvariable=self.settings_stringvars[k], width=self.editor_width)
            self.settings_widgets[k].grid(row=row_s, column=1, padx=2, pady=2, sticky="w")
            self.settings_buttons[k] = ttk.Button(self.scroll_frame, text='...', command=swb[2], width=10)
            self.settings_buttons[k].grid(row=row_s, column=2, padx=2, pady=2, sticky="w")

        row_s += 1
        k = "threads"
        self.settings_labels[k] = ttk.Label(self.scroll_frame, text="Parallel stitching processes:", anchor='e', width=25)
        self.settings_labels[k].grid(row=row_s, column=0, padx=2, pady=2, sticky="e")
        self.settings_widgets[k] = ttk.Combobox(self.scroll_frame,
                                                textvariable=self.settings_stringvars[k],
                                                values=("1", "2", "3", "4"))
        self.settings_widgets[k].config(width=self.editor_width-2, state="readonly")
        self.settings_widgets[k].grid(row=row_s, column=1, padx=2, pady=2, sticky="w")
        ttk.Label(self.scroll_frame, text="values >1 depend on available VRAM.", anchor='w').grid(row=row_s, column=2, padx=2, pady=2, sticky="w")

        row_s += 1
        ttk.Label(self.scroll_frame, text="Input", anchor='se', font=('Arial',16, 'underline')).grid(row=row_s, column=0, padx=2, pady=12, sticky="e")

        row_s += 1
        k = "source_filter"
        self.settings_labels[k] = ttk.Label(self.scroll_frame, text="Source folder filter:", anchor='e', width=25)
        self.settings_labels[k].grid(row=row_s, column=0, padx=2, pady=2, sticky="e")
        self.settings_widgets[k] = ttk.Entry(self.scroll_frame, textvariable=self.settings_stringvars[k], width=self.editor_width)
        self.settings_widgets[k].grid(row=row_s, column=1, padx=2, pady=2, sticky="w")
        ttk.Label(self.scroll_frame, text="Filter folders to be stitched. Default is VID_", anchor='w').grid(row=row_s, column=2, padx=2, pady=2, sticky="w")

        row_s += 1
        k = "min_recording_duration"
        self.settings_labels[k] = ttk.Label(self.scroll_frame, text="Skip videos shorter than", anchor='e', width=25)
        self.settings_labels[k].grid(row=row_s, column=0, padx=2, pady=2, sticky="e")
        self.settings_widgets[k] = ttk.Entry(self.scroll_frame, textvariable=self.settings_stringvars[k], width=self.editor_width)
        self.settings_widgets[k].grid(row=row_s, column=1, padx=2, pady=2, sticky="w")
        ttk.Label(self.scroll_frame, text="Seconds", anchor='w').grid(row=row_s, column=2, padx=2, pady=2, sticky="w")

        row_s += 1
        k = "decode_use_hardware"
        self.settings_labels[k] = ttk.Label(self.scroll_frame, text="Use hardware decoding:", anchor='e', width=25)
        self.settings_labels[k].grid(row=row_s, column=0, padx=2, pady=2, sticky="e")
        self.settings_widgets[k] = ttk.Checkbutton(self.scroll_frame, variable=self.settings_intvars[k])
        self.settings_widgets[k].grid(row=row_s, column=1, padx=2, pady=2, sticky="w")
        ttk.Label(self.scroll_frame, text="Default is on", anchor='w').grid(row=row_s, column=2, padx=2, pady=2, sticky="w")

        row_s += 1
        k = "decode_hardware_count"
        self.settings_labels[k] = ttk.Label(self.scroll_frame, text="Hardware decoding count:", anchor='e', width=25)
        self.settings_labels[k].grid(row=row_s, column=0, padx=2, pady=2, sticky="e")
        self.settings_widgets[k] = ttk.Combobox(self.scroll_frame,
                                                textvariable=self.settings_stringvars[k],
                                                values=("1", "2", "3", "4", "5", "6", "7", "8"))
        self.settings_widgets[k].config(width=self.editor_width-2, state="readonly")
        self.settings_widgets[k].grid(row=row_s, column=1, padx=2, pady=2, sticky="w")
        ttk.Label(self.scroll_frame, text="Default is 6", anchor='w').grid(row=row_s, column=2, padx=2, pady=2, sticky="w")


        row_s += 1
        ttk.Label(self.scroll_frame, text="Stitch", anchor='se', font=('Arial',16, 'underline')).grid(row=row_s, column=0, padx=2, pady=12, sticky="e")

        row_s += 1
        k = "blend_mode"
        self.settings_labels[k] = ttk.Label(self.scroll_frame, text="Stitching mode:", anchor='e', width=25)
        self.settings_labels[k].grid(row=row_s, column=0, padx=2, pady=2, sticky="e")
        self.settings_widgets[k] = ttk.Combobox(self.scroll_frame,
                                                textvariable=self.settings_stringvars[k],
                                                values=("pano", "stereo_top_left", "stereo_top_right", "vr180", "vr180_4lens"))
        self.settings_widgets[k].config(width=self.editor_width-2, state="readonly")
        self.settings_widgets[k].grid(row=row_s, column=1, padx=2, pady=2, sticky="w")
        ttk.Label(self.scroll_frame, text="Default is pano (= Monoscopic)", anchor='w').grid(row=row_s, column=2, padx=2, pady=2, sticky="w")

        row_s += 1
        k = "blender_type"
        blender_type_values = ("auto", "cuda", "opencl", "cpu")
        blender_type_label = "Cuda only on Nvidia cards"
        if platform == "darwin":
            blender_type_values = ("auto", "opencl", "cpu")
            blender_type_label = "opencl for best performance on macOS"
        self.settings_labels[k] = ttk.Label(self.scroll_frame, text="Blender type:", anchor='e', width=25)
        self.settings_labels[k].grid(row=row_s, column=0, padx=2, pady=2, sticky="e")
        self.settings_widgets[k] = ttk.Combobox(self.scroll_frame,
                                                textvariable=self.settings_stringvars[k],
                                                values=blender_type_values)
        self.settings_widgets[k].config(width=self.editor_width-2, state="readonly")
        self.settings_widgets[k].grid(row=row_s, column=1, padx=2, pady=2, sticky="w")
        ttk.Label(self.scroll_frame, text=blender_type_label, anchor='w').grid(row=row_s, column=2, padx=2, pady=2, sticky="w")

        row_s += 1
        k = "original_offset"
        self.settings_labels[k] = ttk.Label(self.scroll_frame, text="Use original offset:", anchor='e', width=25)
        self.settings_labels[k].grid(row=row_s, column=0, padx=2, pady=2, sticky="e")
        self.settings_widgets[k] = ttk.Checkbutton(self.scroll_frame, variable=self.settings_intvars[k])
        self.settings_widgets[k].grid(row=row_s, column=1, padx=2, pady=2, sticky="w")
        ttk.Label(self.scroll_frame, text="Default is on", anchor='w').grid(row=row_s, column=2, padx=2, pady=2, sticky="w")

        row_s += 1
        k = "zenith_optimisation"
        self.settings_labels[k] = ttk.Label(self.scroll_frame, text="Zenith optimisation", anchor='e', width=25)
        self.settings_labels[k].grid(row=row_s, column=0, padx=2, pady=2, sticky="e")
        self.settings_widgets[k] = ttk.Checkbutton(self.scroll_frame, variable=self.settings_intvars[k])
        self.settings_widgets[k].grid(row=row_s, column=1, padx=2, pady=2, sticky="w")
        ttk.Label(self.scroll_frame, text="Default is off", anchor='w').grid(row=row_s, column=2, padx=2, pady=2, sticky="w")

        row_s += 1
        k = "flowstate_stabilisation"
        self.settings_labels[k] = ttk.Label(self.scroll_frame, text="Stabilization", anchor='e', width=25)
        self.settings_labels[k].grid(row=row_s, column=0, padx=2, pady=2, sticky="e")
        self.settings_widgets[k] = ttk.Checkbutton(self.scroll_frame, variable=self.settings_intvars[k])
        self.settings_widgets[k].grid(row=row_s, column=1, padx=2, pady=2, sticky="w")
        ttk.Label(self.scroll_frame, text="Default is on. Turn off for GSV", anchor='w').grid(row=row_s, column=2, padx=2, pady=2, sticky="w")

        row_s += 1
        k = "direction_lock"
        self.settings_labels[k] = ttk.Label(self.scroll_frame, text="Direction lock", anchor='e', width=25)
        self.settings_labels[k].grid(row=row_s, column=0, padx=2, pady=2, sticky="e")
        self.settings_widgets[k] = ttk.Checkbutton(self.scroll_frame, variable=self.settings_intvars[k])
        self.settings_widgets[k].config(width=self.editor_width-2, state="readonly")
        self.settings_widgets[k].grid(row=row_s, column=1, padx=2, pady=2, sticky="w")
        ttk.Label(self.scroll_frame, text="Default is off. Ignored by Stitcher v3", anchor='w').grid(row=row_s, column=2, padx=2, pady=2, sticky="w")

        row_s += 1
        k = "smooth_stitch"
        self.settings_labels[k] = ttk.Label(self.scroll_frame, text="Smooth stitch", anchor='e', width=25)
        self.settings_labels[k].grid(row=row_s, column=0, padx=2, pady=2, sticky="e")
        self.settings_widgets[k] = ttk.Checkbutton(self.scroll_frame, variable=self.settings_intvars[k])
        self.settings_widgets[k].grid(row=row_s, column=1, padx=2, pady=2, sticky="w")
        ttk.Label(self.scroll_frame, text="Default is on", anchor='w').grid(row=row_s, column=2, padx=2, pady=2, sticky="w")

        row_s += 1
        k = "sampling_level"
        self.settings_labels[k] = ttk.Label(self.scroll_frame, text="Sampling type", anchor='e', width=25)
        self.settings_labels[k].grid(row=row_s, column=0, padx=2, pady=2, sticky="e")
        self.settings_widgets[k] = ttk.Combobox(self.scroll_frame,
                                                textvariable=self.settings_stringvars[k],
                                                values=("fast", "medium", "slow"))
        self.settings_widgets[k].config(width=self.editor_width-2, state="readonly")
        self.settings_widgets[k].grid(row=row_s, column=1, padx=2, pady=2, sticky="w")
        ttk.Label(self.scroll_frame, text="Default is fast", anchor='w').grid(row=row_s, column=2, padx=2, pady=2, sticky="w")

        row_s += 1
        k = "reference_time"
        self.settings_labels[k] = ttk.Label(self.scroll_frame, text="Reference second", anchor='e', width=25)
        self.settings_labels[k].grid(row=row_s, column=0, padx=2, pady=2, sticky="e")
        self.settings_widgets[k] = ttk.Entry(self.scroll_frame, textvariable=self.settings_stringvars[k],
                                             width=self.editor_width)
        self.settings_widgets[k].grid(row=row_s, column=1, padx=2, pady=2, sticky="w")
        ttk.Label(self.scroll_frame, text="Set to 0 for middle of recording", anchor='w').grid(row=row_s, column=2, padx=2, pady=2, sticky="w")

        row_s += 1
        k = "trim_start"
        self.settings_labels[k] = ttk.Label(self.scroll_frame, text="Trim start", anchor='e', width=25)
        self.settings_labels[k].grid(row=row_s, column=0, padx=2, pady=2, sticky="e")
        self.settings_widgets[k] = ttk.Entry(self.scroll_frame, textvariable=self.settings_stringvars[k],
                                             width=self.editor_width)
        self.settings_widgets[k].grid(row=row_s, column=1, padx=2, pady=2, sticky="w")
        ttk.Label(self.scroll_frame, text="Seconds to trim from beginning", anchor='w').grid(row=row_s, column=2, padx=2, pady=2, sticky="w")

        row_s += 1
        k = "trim_end"
        self.settings_labels[k] = ttk.Label(self.scroll_frame, text="Trim end", anchor='e', width=25)
        self.settings_labels[k].grid(row=row_s, column=0, padx=2, pady=2, sticky="e")
        self.settings_widgets[k] = ttk.Entry(self.scroll_frame, textvariable=self.settings_stringvars[k],
                                             width=self.editor_width)
        self.settings_widgets[k].grid(row=row_s, column=1, padx=2, pady=2, sticky="w")
        ttk.Label(self.scroll_frame, text=">0: Stop after x seconds from beginning", anchor='w').grid(row=row_s, column=2, padx=2, pady=2, sticky="w")
        row_s += 1
        ttk.Label(self.scroll_frame, text="<0: Stop before x seconds from end", anchor='w').grid(
            row=row_s, column=2, padx=2, pady=2, sticky="w")

        row_s += 1
        ttk.Label(self.scroll_frame, text="Orientation", anchor='se', font=('Arial',16, 'underline')).grid(row=row_s, column=0, padx=2, pady=12, sticky="e")

        row_s += 1
        k = "roll_x"
        self.settings_labels[k] = ttk.Label(self.scroll_frame, text="Roll offset", anchor='e', width=25)
        self.settings_labels[k].grid(row=row_s, column=0, padx=2, pady=2, sticky="e")
        self.settings_widgets[k] = ttk.Entry(self.scroll_frame, textvariable=self.settings_stringvars[k],
                                             width=self.editor_width)
        self.settings_widgets[k].grid(row=row_s, column=1, padx=2, pady=2, sticky="w")
        ttk.Label(self.scroll_frame, text="-180 to 180 Degrees, default 0", anchor='w').grid(row=row_s, column=2, padx=2, pady=2, sticky="w")

        row_s += 1
        k = "tilt_y"
        self.settings_labels[k] = ttk.Label(self.scroll_frame, text="Tilt offset", anchor='e', width=25)
        self.settings_labels[k].grid(row=row_s, column=0, padx=2, pady=2, sticky="e")
        self.settings_widgets[k] = ttk.Entry(self.scroll_frame, textvariable=self.settings_stringvars[k],
                                             width=self.editor_width)
        self.settings_widgets[k].grid(row=row_s, column=1, padx=2, pady=2, sticky="w")
        ttk.Label(self.scroll_frame, text="-180 to 180 Degrees, default 0", anchor='w').grid(row=row_s, column=2, padx=2, pady=2, sticky="w")

        row_s += 1
        k = "pan_z"
        self.settings_labels[k] = ttk.Label(self.scroll_frame, text="Pan offset", anchor='e', width=25)
        self.settings_labels[k].grid(row=row_s, column=0, padx=2, pady=2, sticky="e")
        self.settings_widgets[k] = ttk.Entry(self.scroll_frame, textvariable=self.settings_stringvars[k],
                                             width=self.editor_width)
        self.settings_widgets[k].grid(row=row_s, column=1, padx=2, pady=2, sticky="w")
        ttk.Label(self.scroll_frame, text="-180 to 180 Degrees, default 0", anchor='w').grid(row=row_s, column=2, padx=2, pady=2, sticky="w")

        row_s += 1
        ttk.Label(self.scroll_frame, text="Color", anchor='se', font=('Arial',16, 'underline')).grid(row=row_s, column=0, padx=2, pady=12, sticky="e")
        color_settings = ["brightness", "contrast", "highlight", "shadow", "saturation", "temperature", "tint", "sharpness"]
        for k in color_settings:
            row_s += 1
            self.settings_labels[k] = ttk.Label(self.scroll_frame, text=k.title(), anchor='e', width=25)
            self.settings_labels[k].grid(row=row_s, column=0, padx=2, pady=2, sticky="e")
            self.settings_widgets[k] = ttk.Entry(self.scroll_frame, textvariable=self.settings_stringvars[k],
                                                 width=self.editor_width)
            self.settings_widgets[k].grid(row=row_s, column=1, padx=2, pady=2, sticky="w")
            ttk.Label(self.scroll_frame, text="-100 to 100, default 0", anchor='w').grid(row=row_s, column=2, padx=2, pady=2, sticky="w")


        row_s += 1
        ttk.Label(self.scroll_frame, text="Output", anchor='se', font=('Arial',16, 'underline')).grid(row=row_s, column=0, padx=2, pady=12, sticky="e")

        row_s += 1
        k = "output_format"
        self.settings_labels[k] = ttk.Label(self.scroll_frame, text="File format:", anchor='e', width=25)
        self.settings_labels[k].grid(row=row_s, column=0, padx=2, pady=2, sticky="e")
        self.settings_widgets[k] = ttk.Combobox(self.scroll_frame,
                                                textvariable=self.settings_stringvars[k],
                                                values=("mp4", "mov",))
        self.settings_widgets[k].config(width=self.editor_width-2, state="readonly")
        self.settings_widgets[k].grid(row=row_s, column=1, padx=2, pady=2, sticky="w")
        ttk.Label(self.scroll_frame, text="default is mp4, prores requires mov", anchor='w').grid(row=row_s, column=2, padx=2, pady=2,sticky="w")

        row_s += 1
        k = "output_codec"
        self.settings_labels[k] = ttk.Label(self.scroll_frame, text="Codec type:", anchor='e', width=25)
        self.settings_labels[k].grid(row=row_s, column=0, padx=2, pady=2, sticky="e")
        self.settings_widgets[k] = ttk.Combobox(self.scroll_frame,
                                                textvariable=self.settings_stringvars[k],
                                                values=("h264", "h265", "prores",))
        self.settings_widgets[k].config(width=self.editor_width-2, state="readonly")
        self.settings_widgets[k].grid(row=row_s, column=1, padx=2, pady=2, sticky="w")
        ttk.Label(self.scroll_frame, text="h264 or prores for editing, h265 for Quest", anchor='w').grid(row=row_s, column=2, padx=2, pady=2,sticky="w")

        row_s += 1
        k = "width"
        self.settings_labels[k] = ttk.Label(self.scroll_frame, text="Width:", anchor='e', width=25)
        self.settings_labels[k].grid(row=row_s, column=0, padx=2, pady=2, sticky="e")
        self.settings_widgets[k] = ttk.Combobox(self.scroll_frame,
                                                textvariable=self.settings_stringvars[k],
                                                values=("7680", "6400", "5760", "5248", "5120", "4096", "3840", "2560", "2048", "1920", "1440", "1024", "720"))
        self.settings_widgets[k].config(width=self.editor_width-2)
        self.settings_widgets[k].grid(row=row_s, column=1, padx=2, pady=2, sticky="w")
        ttk.Label(self.scroll_frame, text="Height is set automatically", anchor='w').grid(row=row_s, column=2, padx=2, pady=2, sticky="w")

        row_s += 1
        k = "encode_profile"
        self.settings_labels[k] = ttk.Label(self.scroll_frame, text="Encoding profile", anchor='e', width=25)
        self.settings_labels[k].grid(row=row_s, column=0, padx=2, pady=2, sticky="e")
        self.settings_widgets[k] = ttk.Combobox(self.scroll_frame,
                                                textvariable=self.settings_stringvars[k],
                                                values=("baseline", "main", "high"))
        self.settings_widgets[k].config(width=self.editor_width-2, state="readonly")
        self.settings_widgets[k].grid(row=row_s, column=1, padx=2, pady=2, sticky="w")
        ttk.Label(self.scroll_frame, text="Default is baseline", anchor='w').grid(row=row_s, column=2, padx=2, pady=2, sticky="w")

        row_s += 1
        k = "encode_preset"
        self.settings_labels[k] = ttk.Label(self.scroll_frame, text="Encoding speed", anchor='e', width=25)
        self.settings_labels[k].grid(row=row_s, column=0, padx=2, pady=2, sticky="e")
        self.settings_widgets[k] = ttk.Combobox(self.scroll_frame,
                                                textvariable=self.settings_stringvars[k],
                                                values=("superfast", "veryfast", "faster", "fast", "medium"))
        self.settings_widgets[k].config(width=self.editor_width-2, state="readonly")
        self.settings_widgets[k].grid(row=row_s, column=1, padx=2, pady=2, sticky="w")
        ttk.Label(self.scroll_frame, text="Default is superfast", anchor='w').grid(row=row_s, column=2, padx=2, pady=2, sticky="w")

        row_s += 1
        k = "encode_use_hardware"
        self.settings_labels[k] = ttk.Label(self.scroll_frame, text="Use hardware encoding:", anchor='e', width=25)
        self.settings_labels[k].grid(row=row_s, column=0, padx=2, pady=2, sticky="e")
        self.settings_widgets[k] = ttk.Checkbutton(self.scroll_frame, variable=self.settings_intvars[k])
        self.settings_widgets[k].grid(row=row_s, column=1, padx=2, pady=2, sticky="w")
        ttk.Label(self.scroll_frame, text="Not supported for >4K on all platforms.", anchor='w').grid(row=row_s, column=2, padx=2, pady=2, sticky="w")
        row_s += 1
        ttk.Label(self.scroll_frame, text="Supported for <=4K on most platforms.", anchor='w').grid(row=row_s, column=2, padx=2, pady=2, sticky="w")

        row_s += 1
        k = "bitrate_mbps"
        self.settings_labels[k] = ttk.Label(self.scroll_frame, text="Bitrate:", anchor='e', width=25)
        self.settings_labels[k].grid(row=row_s, column=0, padx=2, pady=2, sticky="e")
        self.settings_widgets[k] = ttk.Combobox(self.scroll_frame,
                                                textvariable=self.settings_intvars[k],
                                                values=("60", "120", "240", "480", "960", "1920", "4090"))
        self.settings_widgets[k].config(width=self.editor_width-2)
        self.settings_widgets[k].grid(row=row_s, column=1, padx=2, pady=2, sticky="w")
        ttk.Label(self.scroll_frame, text="Mbps. Use 1920 or higher for prores.", anchor='w').grid(row=row_s, column=2, padx=2, pady=2, sticky="w")

        row_s += 1
        k = "output_fps"
        self.settings_labels[k] = ttk.Label(self.scroll_frame, text="Target frame rate:", anchor='e', width=25)
        self.settings_labels[k].grid(row=row_s, column=0, padx=2, pady=2, sticky="e")
        self.settings_widgets[k] = ttk.Combobox(self.scroll_frame,
                                                textvariable=self.settings_stringvars[k],
                                                values=("default", "29.97", "30", "60", "59.94", "25", "24", "23.98", "5", "1",))
        self.settings_widgets[k].config(width=self.editor_width-2, state="readonly")
        self.settings_widgets[k].grid(row=row_s, column=1, padx=2, pady=2, sticky="w")
        ttk.Label(self.scroll_frame, text="'Default' uses recording frame rate.", anchor='w').grid(row=row_s, column=2, padx=2, pady=2, sticky="w")

        # Setting the audio type wrong leads to error -11 during stitching.
        row_s += 1
        k = "audio_type"
        self.settings_labels[k] = ttk.Label(self.scroll_frame, text="Audio type", anchor='e', width=25)
        self.settings_labels[k].grid(row=row_s, column=0, padx=2, pady=2, sticky="e")
        self.settings_widgets[k] = ttk.Combobox(self.scroll_frame,
                                                textvariable=self.settings_stringvars[k],
                                                values=("default", "none"))
        self.settings_widgets[k].config(width=self.editor_width-2, state="readonly")
        self.settings_widgets[k].grid(row=row_s, column=1, padx=2, pady=2, sticky="w")
        ttk.Label(self.scroll_frame, text="'Default' uses audio type of the recording.", anchor='w').grid(row=row_s, column=2, padx=2,
                                                                                        pady=2, sticky="w")
        row_s += 1
        ttk.Label(self.scroll_frame, text="Set to 'none' for no audio.", anchor='w').grid(row=row_s, column=2, padx=2, pady=2, sticky="w")

        row_s += 1
        ttk.Label(self.scroll_frame, text="Post processing", anchor='se', font=('Arial',16, 'underline')).grid(row=row_s, column=0, padx=2, pady=12, sticky="e")

        row_s += 1
        k = "rename_after_stitching"
        self.settings_labels[k] = ttk.Label(self.scroll_frame, text="Rename processed folders", anchor='e', width=25)
        self.settings_labels[k].grid(row=row_s, column=0, padx=2, pady=2, sticky="e")
        self.settings_widgets[k] = ttk.Checkbutton(self.scroll_frame, variable=self.settings_intvars[k])
        self.settings_widgets[k].grid(row=row_s, column=1, padx=2, pady=2, sticky="w")

        row_s += 1
        k = "rename_prefix"
        self.settings_labels[k] = ttk.Label(self.scroll_frame, text="Prefix processed folders with", anchor='e', width=25)
        self.settings_labels[k].grid(row=row_s, column=0, padx=2, pady=2, sticky="e")
        self.settings_widgets[k] = ttk.Entry(self.scroll_frame, textvariable=self.settings_stringvars[k], width=self.editor_width)
        self.settings_widgets[k].grid(row=row_s, column=1, padx=2, pady=2, sticky="w")

        row_s += 1
        ttk.Label(self.scroll_frame, text=" ", anchor='w').grid(row=row_s, column=0,padx=2, pady=2,sticky="w")

    def show(self):
        row = 0
        label1 = ttk.Label(self.root, text='Stitch multiple Insta360 Pro 2 video recordings from a common source folder with the same settings.', font=('Arial', 16))
        label1.grid(row=row, column=0, columnspan=3, padx=50, pady=(20,5), sticky="w")

        row += 1
        label1 = ttk.Label(self.root, text='Provided by Mantis Sub underwater housing for Insta360 Pro/Pro 2.')
        label1.grid(row=row, column=0, columnspan=3, padx=50, pady=(5,15), sticky="w")

        row += 1
        ttk.Label(self.root, text="Settings", anchor='w').grid(row=row, column=0, padx=50, pady=5, sticky="w")

        row += 1
        self._create_scroll_frame(row)
        self._populate_scroll_frame()
        self._resize_scroll_frame(self.scroll_width, self.scroll_height)

        row += 1
        ttk.Label(self.root, text="Progress", anchor='w').grid(row=row, column=0, padx=50, pady=(20,5), sticky="w")

        row += 1
        self.text_area = scrolledtext.ScrolledText(self.root, wrap=tk.NONE, height=8, bg='grey', fg='white')
        self.text_area.config(state=tk.DISABLED)
        self.text_area.grid(column=0, row=row, columnspan=3, pady=10, padx=50, sticky="ew")

        row += 1
        self.button_cancel = ttk.Button(text='Cancel', command=self._on_cancel, width=self.button_width)
        self.button_cancel.grid(row=row, column=0, padx=(100,0), pady=(15,50), sticky="w")
        self.button_start = ttk.Button(text='Start', command=self._on_start, width=self.button_width)
        self.button_start.grid(row=row, column=2, padx=(0,100), pady=(15,50), sticky="e")

        # update theme
        self.set_theme(0)

        # run blocking main loop
        self.root.mainloop()
        return 0


def run():
    b = BatchStitcher()
    b.init()
    b.show()


if __name__ == "__main__":
    run()
