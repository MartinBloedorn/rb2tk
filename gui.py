import rb2tk

from platformdirs import user_config_dir
import threading

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext, font

import configparser
import logging
import math
import sys
import os

# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
# NOTICE:
#
# This GUI is an QoL add-on to the rb2tk script. As it implements no core
# functionality, it was mostly AI-generated.
# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #


APP_NAME    = "rb2tk_gui"
APP_VERSION = rb2tk.RB2TK_VERSION


# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
# rb2tk_gui
#
# Installer: pyinstaller gui.py --name "rb2tk_gui" 
#               --windowed --onefile
#               --icon=assets/rb2tk_ico.icns
# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #


class TextHandler(logging.Handler):
    def __init__(self, text_widget):
        super().__init__()
        self.text_widget = text_widget

    def emit(self, record):
        msg = self.format(record)
        self.text_widget.configure(state='normal')
        self.text_widget.insert(tk.END, msg + '\n')
        self.text_widget.see(tk.END)
        self.text_widget.configure(state='disabled')


class ToolTip:
    """Basic tooltip for widgets."""
    def __init__(self, widget, text='widget info'):
        self.widget = widget
        self.text = text
        self.tipwindow = None
        widget.bind("<Enter>", self.show_tip)
        widget.bind("<Leave>", self.hide_tip)

    def show_tip(self, event=None):
        if self.tipwindow or not self.text:
            return
        x, y, cx, cy = self.widget.bbox("insert") if self.widget.bbox("insert") else (0,0,0,0)
        x = x + self.widget.winfo_rootx() + 25
        y = y + cy + self.widget.winfo_rooty() + 25
        self.tipwindow = tw = tk.Toplevel(self.widget)
        tw.wm_overrideredirect(True)  # Remove window decorations
        tw.wm_geometry(f"+{x}+{y}")
        label = tk.Label(tw, text=self.text, justify=tk.LEFT,
                         background="#ffffe0", relief=tk.SOLID, borderwidth=1,
                         font=("tahoma", "8", "normal"))
        label.pack(ipadx=1)

    def hide_tip(self, event=None):
        tw = self.tipwindow
        self.tipwindow = None
        if tw:
            tw.destroy()


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(APP_NAME + " v" + APP_VERSION)

        self._create_menu()
        self._create_library_panel()
        self._create_options_panel()
        self._create_log_panel()

        # Run button
        button_frame = ttk.Frame(self)
        button_frame.pack(fill=tk.X, padx=10, pady=5, anchor='se')

        run_button = ttk.Button(button_frame, text="Run", command=self.on_run)
        run_button.pack(side=tk.RIGHT)

        # Log formatting
        log_formatter = logging.Formatter('%(levelname)s @ %(funcName)s: %(message)s')

        stdout_handler = logging.StreamHandler(sys.stdout)
        stdout_handler.setFormatter(log_formatter)

        text_handler = TextHandler(self.log_output)
        text_handler.setFormatter(log_formatter)

        logger = logging.getLogger()
        logger.setLevel(logging.INFO)
        logger.addHandler(stdout_handler)
        logger.addHandler(text_handler)
        
        logger.info("Hover your mouse over any element for more information.")

        # Set up geometry and shutdown behavior
        minsize = [700, 500]

        self.minsize(*minsize)
        self.after_idle(lambda: (self.geometry("x".join(map(str,minsize))), self._restore_config()))
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        
    def _create_library_panel(self):
        library_frame = ttk.LabelFrame(self, text="Library", padding=10)
        library_frame.pack(fill=tk.X, padx=10, pady=5)

        self.rb_xml_in  = self._create_labeled_filepicker(library_frame, "Rekordbox XML", "open", 0, "Input Rekordbox XML file.")
        self.tk_nml_out = self._create_labeled_filepicker(library_frame, "Traktor NML", "save", 1, "Target path of generated Traktor NML collection.")

        self.merge_var = tk.BooleanVar()
        merge_cb = ttk.Checkbutton(library_frame, text="Merge output", variable=self.merge_var)
        merge_cb.grid(row=2, column=0, sticky="w", pady=(10, 0))
        ToolTip(merge_cb, "Merges the newly generated tracks & playlists into the existing Traktor collection.")

        ttk.Label(library_frame, text="Parent folder").grid(row=3, column=0, sticky="w", pady=(10, 0))
        self.parent_folder_var = tk.StringVar()
        parent_entry = ttk.Entry(library_frame, textvariable=self.parent_folder_var)
        parent_entry.grid(row=3, column=1, sticky="ew", padx=(5, 0))
        ToolTip(parent_entry, "Name of parent folder where Rekorbox playlists will be exported. "
                "Folder will be created at the root level of the collection, replacing any existing entry.")
        library_frame.columnconfigure(1, weight=1)

    def _create_options_panel(self):
        options_frame = ttk.LabelFrame(self, text="Options", padding=10)
        options_frame.pack(fill=tk.X, padx=10, pady=5)

        # Fix cue positions checkbox
        self.fix_cue_var = tk.BooleanVar()
        fix_cue_cb = ttk.Checkbutton(options_frame, text="Fix cue positions", variable=self.fix_cue_var)
        fix_cue_cb.grid(row=0, column=0, sticky="w")
        ToolTip(fix_cue_cb, "Compensates cue offsets caused by codec handling differences. Requires access to all files in the XML library.")

        # Smoothen grid markers checkbox
        self.smooth_grid_var = tk.BooleanVar()
        smooth_grid_cb = ttk.Checkbutton(options_frame, text="Smoothen grid markers", variable=self.smooth_grid_var)
        smooth_grid_cb.grid(row=0, column=1, sticky="w", padx=10)
        ToolTip(smooth_grid_cb, "Prunes redundant (i.e., <0.5% BPM change) grid markers that Rekordbox might generate, "
                "which clutter the visualization in Traktor.")

        # Backup existing collection checkbox
        self.backup_var = tk.BooleanVar()
        backup_cb = ttk.Checkbutton(options_frame, text="Backup existing collection", variable=self.backup_var)
        backup_cb.grid(row=0, column=2, sticky="w", padx=10)#pady=(5,0))
        ToolTip(backup_cb, "Automatically backup the existing collection before creating a new one.")

        # Loop quantization label + dropdown
        loop_quant_label = ttk.Label(options_frame, text="Loop quantization:")
        loop_quant_label.grid(row=1, column=0, sticky="w", pady=(5,0))#, padx=(10,0))
        self.loop_quant_options = ["None", "4 beats", "2 beats", "1 beat", "1/2 beat", "1/4 beat"]
        self.loop_quant_var = tk.StringVar(value=self.loop_quant_options[0])
        loop_quant_dropdown = ttk.OptionMenu(options_frame, self.loop_quant_var, self.loop_quant_var.get(), *self.loop_quant_options)
        loop_quant_dropdown.grid(row=1, column=1, sticky="w", pady=(5,0))
        ToolTip(loop_quant_label, "Quantizes exported Cue-Loops to the selected beat fraction.")

        # Make options_frame columns expand nicely
        options_frame.columnconfigure(2, weight=1)

    def _create_log_panel(self):
        log_frame = ttk.LabelFrame(self, text="Log")
        log_frame.pack(fill="both", expand=True, padx=10, pady=10)

        # Log text widget
        self.log_output = tk.Text(log_frame, height=5, wrap=tk.NONE, state="disabled", font=("Courier", 10))
        self.log_output.pack(fill="both", expand=True, padx=5, pady=5)

        # Button row frame
        button_frame = ttk.Frame(log_frame)
        button_frame.pack(anchor="w", padx=5, pady=5)

        clear_button = ttk.Button(button_frame, text="Clear Log", command=self._clear_log)
        clear_button.pack(side="left", padx=(0, 5))

        save_button = ttk.Button(button_frame, text="Save Log", command=self._save_log)
        save_button.pack(side="left")

    def _clear_log(self):
        self.log_output.config(state="normal")
        self.log_output.delete("1.0", "end")
        self.log_output.config(state="disabled")

    def _save_log(self):
        from tkinter import filedialog

        file_path = filedialog.asksaveasfilename(
            defaultextension=".log",
            filetypes=[("Log files", "*.log"), ("Text files", "*.txt"), ("All files", "*.*")]
        )
        if file_path:
            with open(file_path, "w") as f:
                f.write(self.log_output.get("1.0", "end-1c"))

    def _create_menu(self):
        menubar = tk.Menu(self)
        self.config(menu=menubar)

        # File menu
        # file_menu = tk.Menu(menubar, tearoff=0)
        # file_menu.add_command(label="Open", command=self.menu_open)
        # file_menu.add_command(label="Save", command=self.menu_save)
        # menubar.add_cascade(label="File", menu=file_menu)

        # Help menu
        help_menu = tk.Menu(menubar, tearoff=0)
        help_menu.add_command(label="About", command=self.menu_about)
        menubar.add_cascade(label="Help", menu=help_menu)

    def _create_labeled_filepicker(self, parent, label_text, mode, row, tooltip_text):
        ttk.Label(parent, text=label_text).grid(row=row, column=0, sticky="w")
        var = tk.StringVar()
        entry = ttk.Entry(parent, textvariable=var)
        entry.grid(row=row, column=1, sticky="ew", padx=(5, 5))
        ToolTip(entry, tooltip_text)

        button = ttk.Button(parent, text="...", width=3,
                            command=lambda: self._browse_file(var, mode))
        button.grid(row=row, column=2, sticky="e")

        ToolTip(button, f"Browse to select file ({mode})")

        setattr(self, f"{label_text.lower().replace(' ', '_').replace(':','')}_var", var)
        parent.columnconfigure(1, weight=1)

        return var
    
    # Menu commands
    def menu_open(self):
        file_path = filedialog.askopenfilename()
        if file_path:
            self.input_file_var.set(file_path)
            self.logging(f"Opened file: {file_path}\n")

    def menu_save(self):
        file_path = filedialog.asksaveasfilename()
        if file_path:
            self.output_file_var.set(file_path)
            self.logging(f"Saved file: {file_path}\n")

    def menu_about(self):
        messagebox.showinfo("About", "rb2tk\nConvert your Rekordbox Library to Traktor\n\nby Martin Bloedorn\nmartinvb.com")

    def _get_config_path(self):
        config_dir = user_config_dir(APP_NAME)
        os.makedirs(config_dir, exist_ok=True)
        return os.path.join(config_dir, f"{APP_NAME}.ini")
    
    def _generate_config(self):
        loop_quant = 0.0
        if self.loop_quant_var.get() != self.loop_quant_options[0]:
            loop_quant = float(self.loop_quant_options.index(self.loop_quant_var.get()) - 1)
            loop_quant = 1.0/(math.pow(2.0, loop_quant))
            logging.debug(loop_quant)

        config = configparser.ConfigParser()
        config["Meta"] = {}
        config["Library"] = {}
        config["Options"] = {}

        config["Library"]["RekordboxXmlInput"] = self.rb_xml_in.get()
        config["Library"]["TraktorNmlOutput"] = self.tk_nml_out.get()

        config["Options"]["BackupExistingCollection"] = "yes" if self.backup_var.get() else "no"
        config["Options"]["SmoothenGridMarkers"] = "yes" if self.smooth_grid_var.get() else "no"
        config["Options"]["FixCuePositions"] = "yes" if self.fix_cue_var.get() else "no"
        config["Options"]["ParentPlaylistFolder"] = self.parent_folder_var.get()
        config["Options"]["LoopQuantization"] = str(loop_quant)

        config["Meta"]["Version"] = APP_VERSION

        return config

    def _save_config(self):
        config = self._generate_config()
        path = self._get_config_path()
        try:
            with open(path, "w") as f:
                logging.info("Saving state to: " + path)
                config.write(f)
        except:
            print("Failed to save config.")

    def _restore_config(self):
        path = self._get_config_path()
        config = configparser.ConfigParser()
        
        if not os.path.exists(path):
            logging.info("Using defaults - no config found at: " + path)
        else:
            config.read(path)

        self.merge_var.set(config.get("Library", "MergeOutput", fallback="yes") == "yes")
        self.rb_xml_in.set(config.get("Library", "RekordboxXmlInput", fallback="/path/to/rekordbox.xml"))
        self.tk_nml_out.set(config.get("Library", "TraktorNmlOutput", fallback="/path/to/traktor.nml"))

        self.backup_var.set(config.get("Options", "BackupExistingCollection", fallback="yes") == "yes")
        self.fix_cue_var.set(config.get("Options", "FixCuePositions", fallback="yes") == "yes")
        self.smooth_grid_var.set(config.get("Options", "SmoothenGridMarkers", fallback="yes") == "yes")
        self.parent_folder_var.set(config.get("Options", "ParentPlaylistFolder", fallback="rekordbox"))

        self.loop_quant_var.set(self.loop_quant_options[0]) # default to 'None' 
        loop_quant = float(config.get("Options", "LoopQuantization", fallback="1.0"))
        if loop_quant >= 1.0/8.0:
            i = round(-1.0*math.log2(loop_quant)) + 1
            self.loop_quant_var.set(self.loop_quant_options[min(i, len(self.loop_quant_options) - 1)])

    def _on_close(self):
        self._save_config()
        self.destroy()

    def _browse_file(self, var, mode):
        if mode == "open":
            file_path = filedialog.askopenfilename()
        else:
            file_path = filedialog.asksaveasfilename()
        if file_path:
            var.set(file_path)

    def run_rb2tk(self):
        result = False
        try:
            logging.info("Starting " + APP_NAME + " v" + APP_VERSION)
            config = self._generate_config()

            rr = rb2tk.RekordboxReader(config)
            tw = rb2tk.TraktorWriter(config)
            oo = rb2tk.OptionalOperations(config)

            lib = rr.read(config["Library"]["RekordboxXmlInput"])
            lib = oo.apply(lib)
            result = tw.write(lib, config["Library"]["TraktorNmlOutput"])
        except Exception as e:
            logging.error(str(e))
        else:
            if result:
                logging.info("Done!")

    def on_run(self):
        thread = threading.Thread(target=self.run_rb2tk, daemon=True)
        thread.start()
        

if __name__ == "__main__":
    app = App()
    app.mainloop()
