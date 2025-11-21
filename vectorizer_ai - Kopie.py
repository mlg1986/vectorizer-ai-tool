import requests
import tkinter as tk
from tkinter import filedialog, ttk, messagebox
import configparser
import os
from PIL import Image, ImageTk
import threading
import logging
from io import BytesIO

# Versuch, cairosvg zu importieren
try:
    import cairosvg
except ImportError:
    cairosvg = None

try:
    from PIL import Resampling
    resample_method = Resampling.LANCZOS
except ImportError:
    resample_method = Image.LANCZOS

class VectorizerApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Vectorizer AI Tool")
        self.geometry("1200x800")
        self.config_file = 'config.ini'
        self.config = configparser.ConfigParser()

        # Logging konfigurieren
        logging.basicConfig(
            level=logging.DEBUG,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler("vectorizer_app.log", encoding='utf-8'),
                logging.StreamHandler()
            ]
        )
        logging.info("VectorizerApp gestartet.")

        # Variablen
        self.api_key = tk.StringVar()
        self.api_secret = tk.StringVar()
        self.image_path = tk.StringVar()
        self.palette = tk.StringVar()
        self.mode = tk.StringVar(value='preview')  # Standardmodus von 'test' zu 'preview' geändert
        self.output_format = tk.StringVar(value='png')  # Voreinstellung auf 'PNG'
        self.gpl_file_path = tk.StringVar()
        self.width_cm = tk.StringVar()
        self.height_cm = tk.StringVar()
        self.input_dpi = tk.StringVar(value='96')  # Standardwert für Input DPI
        self.output_dpi = tk.StringVar(value='96')  # Standardwert für Output DPI
        self.input_base_folder = tk.StringVar()
        self.output_folder = tk.StringVar()
        self.folder_number = tk.StringVar()
        self.display_image = None
        self.result_image = None
        self.script_dir = os.path.dirname(os.path.abspath(__file__)) if '__file__' in globals() else os.getcwd()
        self.progress_label = None

        # Variablen für Detailgrad, Glättung und maximale Farben in der Hauptoberfläche
        self.line_fit_tolerance = tk.StringVar()
        self.anti_aliasing_mode = tk.StringVar()
        self.max_colors = tk.StringVar(value='36')  # Standardwert auf 36 gesetzt
        self.min_area_px = tk.StringVar(value='50')  # Standardwert auf 50 gesetzt

        self.load_settings()
        self.create_gui()

        # Trace für Mode-Änderungen hinzufügen
        self.mode.trace_add('write', self.on_mode_change)

    def create_gui(self):
        main_frame = ttk.Frame(self)
        main_frame.pack(fill='both', expand=True)

        # Obere Frames für Bedienelemente
        top_frame = ttk.Frame(main_frame)
        top_frame.pack(side='top', fill='x')

        # Bedienelemente links
        controls_frame = ttk.Frame(top_frame)
        controls_frame.pack(side='left', fill='x', expand=True, padx=5, pady=5)

        self.progress_label = ttk.Label(top_frame, text="")
        self.progress_label.pack(side='left', padx=10)

        # Untere Frames für Bilder
        bottom_frame = ttk.Frame(main_frame)
        bottom_frame.pack(side='top', fill='both', expand=True)

        # Eingabe- und Ausgabebilder nebeneinander
        original_frame = ttk.Frame(bottom_frame)
        original_frame.pack(side='left', fill='both', expand=True, padx=5, pady=5)

        original_label = ttk.Label(original_frame, text="Originalbild:")
        original_label.pack(anchor='w')

        self.original_canvas = tk.Canvas(original_frame, bg='grey')
        self.original_canvas.pack(fill='both', expand=True)

        result_frame = ttk.Frame(bottom_frame)
        result_frame.pack(side='left', fill='both', expand=True, padx=5, pady=5)

        result_label = ttk.Label(result_frame, text="Vektorisierte Ausgabe:")
        result_label.pack(anchor='w')

        self.result_canvas = tk.Canvas(result_frame, bg='grey')
        self.result_canvas.pack(fill='both', expand=True)

        # Bedienelemente erstellen
        self.create_controls(controls_frame)

        # Bildanpassung bei Größenänderung
        self.original_canvas.bind("<Configure>", lambda event: self.resize_image(event, original=True))
        self.result_canvas.bind("<Configure>", lambda event: self.resize_image(event, original=False))

    def create_controls(self, parent):
        # Bildauswahl
        frame_manual = ttk.LabelFrame(parent, text="Bildauswahl")
        frame_manual.pack(padx=5, pady=5, fill='x')

        lbl_image = ttk.Label(frame_manual, text="Bilddatei:")
        lbl_image.grid(row=0, column=0, padx=5, pady=5, sticky='w')

        entry_image = ttk.Entry(frame_manual, textvariable=self.image_path)
        entry_image.grid(row=0, column=1, padx=5, pady=5, sticky='ew')

        btn_browse = ttk.Button(frame_manual, text="Durchsuchen", command=self.browse_image)
        btn_browse.grid(row=0, column=2, padx=5, pady=5)

        frame_manual.columnconfigure(1, weight=1)

        # Ordnernummer
        frame_number = ttk.LabelFrame(parent, text="Bild aus Ordner laden")
        frame_number.pack(padx=5, pady=5, fill='x')

        lbl_number = ttk.Label(frame_number, text="Ordnernummer:")
        lbl_number.grid(row=0, column=0, padx=5, pady=5, sticky='w')

        entry_number = ttk.Entry(frame_number, textvariable=self.folder_number)
        entry_number.grid(row=0, column=1, padx=5, pady=5, sticky='w')
        entry_number.bind("<Return>", lambda event: self.load_image_by_number())

        btn_load = ttk.Button(frame_number, text="Laden", command=self.load_image_by_number)
        btn_load.grid(row=0, column=2, padx=5, pady=5)

        # Parameter
        frame_parameters = ttk.LabelFrame(parent, text="Parameter")
        frame_parameters.pack(padx=5, pady=5, fill='x')

        # Maßeingabe
        lbl_width = ttk.Label(frame_parameters, text="Breite (cm):")
        lbl_width.grid(row=0, column=0, padx=5, pady=5, sticky='w')

        entry_width = ttk.Entry(frame_parameters, textvariable=self.width_cm)
        entry_width.grid(row=0, column=1, padx=5, pady=5, sticky='ew')

        lbl_height = ttk.Label(frame_parameters, text="Höhe (cm):")
        lbl_height.grid(row=1, column=0, padx=5, pady=5, sticky='w')

        entry_height = ttk.Entry(frame_parameters, textvariable=self.height_cm)
        entry_height.grid(row=1, column=1, padx=5, pady=5, sticky='ew')

        # Output Format
        lbl_output_format = ttk.Label(frame_parameters, text="Ausgabeformat:")
        lbl_output_format.grid(row=2, column=0, padx=5, pady=5, sticky='w')

        frame_output_format = ttk.Frame(frame_parameters)
        frame_output_format.grid(row=2, column=1, padx=5, pady=5, sticky='w')

        formats = [("PNG", "png"), ("SVG", "svg")]
        self.rb_output_formats = {}  # Dictionary zur Speicherung der Radiobutton-Referenzen
        for text, value in formats:
            rb_format = ttk.Radiobutton(frame_output_format, text=text, variable=self.output_format, value=value)
            rb_format.pack(side='left', padx=5)
            self.rb_output_formats[value] = rb_format  # Speichern der Referenz

        # Mode Selection
        lbl_mode = ttk.Label(frame_parameters, text="Modus:")
        lbl_mode.grid(row=3, column=0, padx=5, pady=5, sticky='w')

        frame_mode = ttk.Frame(frame_parameters)
        frame_mode.grid(row=3, column=1, padx=5, pady=5, sticky='w')

        modes = [("Preview", "preview"), ("Production", "production")]  # "Test" Modus entfernt
        for text, value in modes:
            rb_mode = ttk.Radiobutton(frame_mode, text=text, variable=self.mode, value=value)
            rb_mode.pack(side='left', padx=5)

        # Detailgrad
        lbl_line_fit_tolerance = ttk.Label(frame_parameters, text="Detailgrad (line_fit_tolerance):")
        lbl_line_fit_tolerance.grid(row=4, column=0, padx=5, pady=5, sticky='w')

        entry_line_fit_tolerance = ttk.Entry(frame_parameters, textvariable=self.line_fit_tolerance)
        entry_line_fit_tolerance.grid(row=4, column=1, padx=5, pady=5, sticky='ew')

        # Glättung (Anti-Aliasing)
        lbl_anti_aliasing_mode = ttk.Label(frame_parameters, text="Glättung (anti_aliasing_mode):")
        lbl_anti_aliasing_mode.grid(row=5, column=0, padx=5, pady=5, sticky='w')

        combo_anti_aliasing_mode = ttk.Combobox(frame_parameters, textvariable=self.anti_aliasing_mode, values=['anti_aliased', 'aliased'])
        combo_anti_aliasing_mode.grid(row=5, column=1, padx=5, pady=5, sticky='ew')
        combo_anti_aliasing_mode.current(0)  # Standardwert: 'anti_aliased'

        # Mindestfläche hinzufügen
        lbl_min_area = ttk.Label(frame_parameters, text="Mindestfläche (px):")
        lbl_min_area.grid(row=6, column=0, padx=5, pady=5, sticky='w')

        entry_min_area = ttk.Entry(frame_parameters, textvariable=self.min_area_px)
        entry_min_area.grid(row=6, column=1, padx=5, pady=5, sticky='ew')
        # Die folgende Zeile entfernen, da der Wert bereits im __init__ gesetzt wird
        # entry_min_area.insert(0, '50')

        # Maximale Farben
        lbl_max_colors = ttk.Label(frame_parameters, text="Maximale Farben:")
        lbl_max_colors.grid(row=7, column=0, padx=5, pady=5, sticky='w')

        entry_max_colors = ttk.Entry(frame_parameters, textvariable=self.max_colors)
        entry_max_colors.grid(row=7, column=1, padx=5, pady=5, sticky='ew')

        frame_parameters.columnconfigure(1, weight=1)

        # Buttons in einer Zeile
        button_frame = ttk.Frame(parent)
        button_frame.pack(padx=5, pady=10, fill='x')

        btn_start = ttk.Button(button_frame, text="Vektorisieren", command=self.start_vectorization_thread)
        btn_start.pack(side='left', padx=5, pady=5)

        btn_settings = ttk.Button(button_frame, text="Einstellungen", command=self.open_settings_window)
        btn_settings.pack(side='left', padx=5, pady=5)

        btn_open_images = ttk.Button(button_frame, text="Bilder in neuem Fenster öffnen", command=self.open_images_in_new_window)
        btn_open_images.pack(side='left', padx=5, pady=5)

    def browse_image(self):
        file_path = filedialog.askopenfilename(filetypes=[("Bilddateien", "*.bmp;*.gif;*.jpeg;*.jpg;*.png;*.tiff;*.svg")])
        if file_path:
            self.image_path.set(file_path)
            self.display_image_on_canvas(file_path, original=True)
            self.calculate_image_dimensions(file_path)

    def calculate_image_dimensions(self, image_path):
        try:
            with Image.open(image_path) as img:
                dpi = img.info.get('dpi', (96, 96))
                width_inch = img.width / dpi[0]
                height_inch = img.height / dpi[1]
                width_cm = round(width_inch * 2.54, 2)
                height_cm = round(height_inch * 2.54, 2)
                self.width_cm.set(str(width_cm))
                self.height_cm.set(str(height_cm))
                logging.debug(f"Berechnete Maße: {width_cm} cm x {height_cm} cm")
        except Exception as e:
            logging.error(f"Fehler beim Berechnen der Bildmaße: {e}")

    def display_image_on_canvas(self, image_path, original=True, canvas=None, photo_holder=None):
        try:
            if image_path.lower().endswith('.svg'):
                if cairosvg is None:
                    messagebox.showwarning("Warnung", "Die Anzeige von SVG-Dateien erfordert das 'cairosvg' Modul.")
                    logging.warning("SVG-Datei angezeigt, aber 'cairosvg' ist nicht installiert.")
                    return
                else:
                    try:
                        # Verbesserte Behandlung von UNC-Pfaden
                        normalized_path = os.path.normpath(image_path)
                        if normalized_path.startswith('\\\\'):
                            # UNC-Pfad korrekt formatieren
                            file_url = 'file:' + normalized_path.replace('\\', '/')
                        else:
                            # Lokaler Pfad
                            file_url = 'file:///' + normalized_path.replace('\\', '/')
                        
                        logging.debug(f"Versuche SVG zu laden von: {file_url}")
                        png_data = cairosvg.svg2png(url=file_url)
                        img = Image.open(BytesIO(png_data))
                    except Exception as e:
                        logging.error(f"Fehler beim Konvertieren der SVG-Datei: {e}")
                        # Versuche alternative Methode mit direktem Lesen
                        try:
                            with open(image_path, 'rb') as svg_file:
                                svg_content = svg_file.read()
                                png_data = cairosvg.svg2png(bytestring=svg_content)
                                img = Image.open(BytesIO(png_data))
                                logging.info("SVG erfolgreich mit alternativer Methode geladen")
                        except Exception as e2:
                            logging.error(f"Auch alternative Methode fehlgeschlagen: {e2}")
                            messagebox.showerror("Fehler", f"Fehler beim Konvertieren der SVG-Datei:\n{e2}")
                            return
            else:
                img = Image.open(image_path)

            if not canvas:
                canvas = self.original_canvas if original else self.result_canvas
            canvas_width = canvas.winfo_width()
            canvas_height = canvas.winfo_height()
            if canvas_width <= 1 or canvas_height <= 1:
                self.update_idletasks()
                canvas_width = canvas.winfo_width()
                canvas_height = canvas.winfo_height()
            img_ratio = img.width / img.height
            canvas_ratio = canvas_width / canvas_height
            if img_ratio > canvas_ratio:
                new_width = canvas_width
                new_height = int(new_width / img_ratio)
            else:
                new_height = canvas_height
                new_width = int(new_height * img_ratio)

            # Sicherstellen, dass die neuen Dimensionen größer als 0 sind
            if new_width <= 0 or new_height <= 0:
                logging.error("Fehler beim Anzeigen des Bildes: Berechnete Bildgröße ist ungültig.")
                return

            img = img.resize((new_width, new_height), resample_method)
            photo = ImageTk.PhotoImage(img)
            if photo_holder is not None:
                if original:
                    photo_holder.original_photo = photo
                else:
                    photo_holder.result_photo = photo
            else:
                if original:
                    self.display_image = photo
                else:
                    self.result_image = photo
            canvas.delete("all")
            canvas.create_image(canvas_width / 2, canvas_height / 2, image=photo)
            canvas.image = photo  # Referenz speichern
        except Exception as e:
            messagebox.showerror("Fehler", f"Fehler beim Anzeigen des Bildes:\n{e}")
            logging.error(f"Fehler beim Anzeigen des Bildes: {e}")

    def resize_image(self, event, original=True, canvas=None):
        image_path = self.image_path.get() if original else getattr(self, 'output_path', '')
        if image_path and os.path.exists(image_path):
            self.display_image_on_canvas(image_path, original=original, canvas=canvas)

    def load_image_by_number(self):
        folder_number = self.folder_number.get().strip()
        input_base = self.input_base_folder.get().strip()
        if not folder_number:
            messagebox.showerror("Fehler", "Bitte geben Sie eine Ordnernummer ein.")
            logging.error("Keine Ordnernummer eingegeben.")
            return
        if not input_base:
            messagebox.showerror("Fehler", "Bitte legen Sie den Input Basisordner in den Einstellungen fest.")
            logging.error("Input Basisordner nicht festgelegt.")
            return

        # Amazon-Bestellnummern verarbeiten
        folder_number_processed = folder_number.split('-')[0]  # Ignoriere alles nach dem ersten '-'
        logging.debug(f"Verarbeitete Ordnernummer: {folder_number_processed}")

        try:
            matching_folders = [f for f in os.listdir(input_base)
                                if os.path.isdir(os.path.join(input_base, f)) and f.startswith(folder_number_processed)]
        except Exception as e:
            messagebox.showerror("Fehler", f"Fehler beim Durchsuchen des Input Basisordners:\n{e}")
            logging.error(f"Fehler beim Durchsuchen des Input Basisordners: {e}")
            return
        if not matching_folders:
            messagebox.showerror("Fehler", f"Kein Unterordner mit der Nummer {folder_number_processed} gefunden.")
            logging.error(f"Kein Unterordner mit der Nummer {folder_number_processed} gefunden.")
            return

        # Wenn mehrere Ordner gefunden wurden, Auswahl anzeigen
        if len(matching_folders) > 1:
            selected_folder = self.select_folder_dialog(matching_folders)
            if not selected_folder:
                logging.info("Keine Ordnerauswahl getroffen.")
                return
        else:
            selected_folder = matching_folders[0]

        target_folder = os.path.join(input_base, selected_folder)
        input_image_path = os.path.join(target_folder, 'input.png')
        if not os.path.exists(input_image_path):
            messagebox.showerror("Fehler", f"Die Datei 'input.png' wurde im Ordner {target_folder} nicht gefunden.")
            logging.error(f"Die Datei 'input.png' wurde im Ordner {target_folder} nicht gefunden.")
            return
        self.image_path.set(input_image_path)
        self.display_image_on_canvas(input_image_path, original=True)
        self.calculate_image_dimensions(input_image_path)

    def select_folder_dialog(self, folders):
        selection_window = tk.Toplevel(self)
        selection_window.title("Ordner auswählen")
        selection_window.geometry("400x300")
        ttk.Label(selection_window, text="Mehrere Ordner gefunden. Bitte wählen Sie einen Ordner aus:").pack(pady=10)

        folder_var = tk.StringVar(value=folders[0])

        listbox = tk.Listbox(selection_window, listvariable=tk.StringVar(value=folders), height=10)
        listbox.pack(fill='both', expand=True, padx=10, pady=10)
        listbox.selection_set(0)

        def select_and_close():
            index = listbox.curselection()
            if index:
                folder_var.set(folders[index[0]])
                selection_window.destroy()
            else:
                messagebox.showwarning("Warnung", "Bitte wählen Sie einen Ordner aus.")

        btn_select = ttk.Button(selection_window, text="Auswählen", command=select_and_close)
        btn_select.pack(pady=10)

        self.wait_window(selection_window)
        selected_folder = folder_var.get()
        return selected_folder

    def start_vectorization_thread(self):
        thread = threading.Thread(target=self.vectorize_image)
        thread.start()

    def vectorize_image(self):
        self.progress_label.config(text="Vektorisierung läuft...")
        image_path = self.image_path.get()
        api_key = self.api_key.get()
        api_secret = self.api_secret.get()
        output_format = self.output_format.get()
        mode = self.mode.get()

        # Neue Eingabewerte für Breite, Höhe und DPI
        try:
            width_cm = float(self.width_cm.get())
            height_cm = float(self.height_cm.get())
            input_dpi = float(self.input_dpi.get())
            output_dpi = float(self.output_dpi.get())
            min_area_px = float(self.min_area_px.get())  # Mindestfläche abrufen

            if min_area_px < 45 or min_area_px > 100:
                raise ValueError("Die Mindestfläche muss zwischen 45 und 100 px liegen.")
        except ValueError as ve:
            messagebox.showerror("Fehler", f"Ungültiger Wert: {ve}")
            logging.error(f"Ungültige Eingabewerte: {ve}")
            self.progress_label.config(text="")
            return

        # Data payload für die API
        data = {
            'output.file_format': output_format,
            'mode': mode,
            'processing.strict_palette': 'true',
            'output.size.width': str(width_cm),
            'output.size.height': str(height_cm),
            'output.size.unit': 'cm',
            'output.size.input_dpi': str(input_dpi),
            'output.size.output_dpi': str(output_dpi),
            'output.curves.line_fit_tolerance': self.line_fit_tolerance.get(),
            'output.curves.allowed.quadratic_bezier': 'false',
            'output.curves.allowed.cubic_bezier': 'false',
            'processing.shapes.min_area_px': str(min_area_px)  # Mindestfläche hinzufügen
        }

        # Anti-Aliasing-Parameter nur bei PNG hinzufügen
        if output_format.lower() == 'png':
            data['output.bitmap.anti_aliasing_mode'] = self.anti_aliasing_mode.get()

        # Maximale Farben hinzufügen, wenn angegeben
        if self.max_colors.get():
            data['processing.max_colors'] = self.max_colors.get()

        # Bestimmen des Ausgabe-Dateinamens mit Ordnernummer
        folder_number = self.folder_number.get().strip()
        if folder_number:
            output_filename = f"{folder_number}.{output_format}"
        else:
            base_filename = os.path.basename(image_path)
            name, ext = os.path.splitext(base_filename)
            output_filename = f"{name}_vectorized.{output_format}"

        output_path = os.path.join(self.output_folder.get(), output_filename)
        self.output_path = output_path

        # Daten für die Palette verarbeiten
        palette_str = ''
        num_colors_sent = 0  # Anzahl der Farben, die an die API gesendet werden
        if self.palette.get():
            palette_str = self.palette.get()
            num_colors_sent = len(palette_str.split(';'))
            data['processing.palette'] = palette_str
        elif self.gpl_file_path.get():
            palette_str = self.create_palette_from_gpl(self.gpl_file_path.get())
            if palette_str:
                num_colors_sent = len(palette_str.split(';'))
                data['processing.palette'] = palette_str
        else:
            # Wenn weder eine Palette noch eine GPL-Datei angegeben ist, wird keine Palette gesendet
            pass

        # Logging der gesendeten Daten hinzufügen
        logging.debug(f"Sende Daten an API: {data}")
        logging.debug(f"Sende Bildpfad: {image_path}")

        # API-Anfrage senden
        try:
            with open(image_path, 'rb') as image_file:
                files = {'image': image_file}
                response = requests.post(
                    'https://de.vectorizer.ai/api/v1/vectorize',
                    files=files,
                    data=data,
                    auth=(api_key, api_secret),
                    stream=True
                )

            response_content = response.content

            if response.status_code == 200:
                content_type = response.headers.get('Content-Type', '')
                logging.debug(f"Erhaltener Content-Type: {content_type}")

                # Im Preview-Modus wird das Ausgabeformat auf 'png' gesetzt
                if mode == 'preview':
                    output_format = 'png'

                if output_format == 'svg' and 'svg' not in content_type.lower():
                    # Inhalt der Antwort speichern und anzeigen
                    temp_error_path = os.path.join(self.output_folder.get(), 'error_response.txt')
                    with open(temp_error_path, 'wb') as temp_file:
                        temp_file.write(response_content)
                    error_message = f"Fehlerhafte Antwort erhalten. Der Inhalt ist kein gültiges SVG.\nDie Antwort wurde gespeichert unter: {temp_error_path}"
                    messagebox.showerror("API Fehler", error_message)
                    logging.error(f"Ungültige Antwort erhalten: {response.status_code} - Inhalt wurde in {temp_error_path} gespeichert.")
                    return

                # Speichere die Antwort basierend auf dem Content-Type
                if 'image/svg+xml' in content_type.lower():
                    # Speichere die Antwort als SVG
                    with open(output_path, 'wb') as output_file:
                        output_file.write(response_content)
                    logging.debug(f"SVG-Datei gespeichert unter: {output_path}")
                elif 'image/png' in content_type.lower():
                    # Speichere die Antwort als PNG
                    png_output_path = output_path
                    if not output_path.lower().endswith('.png'):
                        png_output_path = os.path.splitext(output_path)[0] + '.png'
                    with open(png_output_path, 'wb') as output_file:
                        output_file.write(response_content)
                    logging.debug(f"PNG-Datei gespeichert unter: {png_output_path}")
                    # Setze output_path auf die PNG-Datei
                    self.output_path = png_output_path
                else:
                    # Unerwarteter Inhaltstyp
                    temp_error_path = os.path.join(self.output_folder.get(), 'error_response.txt')
                    with open(temp_error_path, 'wb') as temp_file:
                        temp_file.write(response_content)
                    error_message = f"Unerwarteter Inhaltstyp erhalten: {content_type}\nDie Antwort wurde gespeichert unter: {temp_error_path}"
                    messagebox.showerror("API Fehler", error_message)
                    logging.error(f"Unerwarteter Inhaltstyp erhalten: {content_type} - Inhalt wurde in {temp_error_path} gespeichert.")
                    return

                # Anzeige der Anzahl der gesendeten Farben
                messagebox.showinfo("Erfolg", f"Die Vektorisierung war erfolgreich.\nAnzahl der an die API gesendeten Farbcodes: {num_colors_sent}")
                logging.info("Vektorisierung erfolgreich abgeschlossen.")
                # Ergebnisbild anzeigen
                self.display_image_on_canvas(self.output_path, original=False)
            else:
                error_message = f"Fehler: {response.status_code}\n{response.text}"
                messagebox.showerror("API Fehler", error_message)
                logging.error(f"API Fehler: {response.status_code} - {response.text}")
        except Exception as e:
            messagebox.showerror("Fehler", f"Ein Fehler ist aufgetreten:\n{e}")
            logging.error(f"Fehlerdetails: {e}")
        finally:
            self.progress_label.config(text="")
            # Modus zurücksetzen, wenn er auf 'production' war
            if self.mode.get() == 'production':
                self.mode.set('test')
                logging.info("Modus wurde nach Vektorisierung von 'production' auf 'test' zurückgesetzt.")

    def create_palette_from_gpl(self, gpl_path):
        palette = self.read_gpl_file(gpl_path)
        if not palette:
            return None
        palette_str = '; '.join([color[0] for color in palette])  # Nur die Hex-Werte
        return palette_str

    def read_gpl_file(self, file_path):
        palette = []
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            for line in lines:
                line = line.strip()
                if line == '' or line.startswith('#'):
                    continue
                if line.startswith('GIMP Palette'):
                    continue
                if line.startswith('Name:'):
                    continue
                if line.startswith('Columns:'):
                    continue
                # Versuchen, die ersten drei Teile in Zahlen umzuwandeln
                parts = line.strip().split(None, 3)
                if len(parts) >= 3:
                    try:
                        r, g, b = parts[:3]
                        r = int(r)
                        g = int(g)
                        b = int(b)
                        color_hex = '#{:02x}{:02x}{:02x}'.format(r, g, b).lower()
                        palette.append((color_hex, ''))  # Name wird nicht benötigt
                    except ValueError:
                        logging.warning(f"Zeile übersprungen (keine gültigen Farbdaten): {line}")
                        continue
            return palette
        except Exception as e:
            messagebox.showerror("Fehler", f"Fehler beim Lesen der GPL-Datei:\n{e}")
            logging.error(f"Fehler beim Lesen der GPL-Datei: {e}")
            return None

    def open_images_in_new_window(self):
        # Neues Fenster erstellen
        new_window = tk.Toplevel(self)
        new_window.title("Original und Vektorisierte Bilder")
        new_window.geometry("800x600")

        # Frames für Original- und Ergebnisbilder
        original_frame = ttk.Frame(new_window)
        original_frame.pack(side='left', fill='both', expand=True, padx=5, pady=5)

        original_label = ttk.Label(original_frame, text="Originalbild:")
        original_label.pack(anchor='w')

        original_canvas = tk.Canvas(original_frame, bg='grey')
        original_canvas.pack(fill='both', expand=True)

        result_frame = ttk.Frame(new_window)
        result_frame.pack(side='left', fill='both', expand=True, padx=5, pady=5)

        result_label = ttk.Label(result_frame, text="Vektorisierte Ausgabe:")
        result_label.pack(anchor='w')

        result_canvas = tk.Canvas(result_frame, bg='grey')
        result_canvas.pack(fill='both', expand=True)

        # Bilder auf den Canvas-Elementen anzeigen
        if self.image_path.get() and os.path.exists(self.image_path.get()):
            self.display_image_on_canvas(self.image_path.get(), original=True, canvas=original_canvas)
        if hasattr(self, 'output_path') and os.path.exists(self.output_path):
            self.display_image_on_canvas(self.output_path, original=False, canvas=result_canvas)

        # Bildanpassung bei Größenänderung
        original_canvas.bind("<Configure>", lambda event: self.resize_image(event, original=True, canvas=original_canvas))
        result_canvas.bind("<Configure>", lambda event: self.resize_image(event, original=False, canvas=result_canvas))

    def open_settings_window(self):
        settings_window = tk.Toplevel(self)
        settings_window.title("Einstellungen")
        settings_window.geometry("500x600")  # Erhöhte Höhe für zusätzliche Felder
        settings_frame = ttk.Frame(settings_window)
        settings_frame.pack(padx=10, pady=10, fill='both', expand=True)

        lbl_api_key = ttk.Label(settings_frame, text="API Key:")
        lbl_api_key.grid(row=0, column=0, padx=5, pady=5, sticky='w')
        entry_api_key = ttk.Entry(settings_frame, textvariable=self.api_key, show='*')
        entry_api_key.grid(row=0, column=1, padx=5, pady=5, sticky='ew')

        lbl_api_secret = ttk.Label(settings_frame, text="API Secret:")
        lbl_api_secret.grid(row=1, column=0, padx=5, pady=5, sticky='w')
        entry_api_secret = ttk.Entry(settings_frame, textvariable=self.api_secret, show='*')
        entry_api_secret.grid(row=1, column=1, padx=5, pady=5, sticky='ew')

        lbl_input_folder = ttk.Label(settings_frame, text="Input Basisordner:")
        lbl_input_folder.grid(row=2, column=0, padx=5, pady=5, sticky='w')
        frame_input_folder = ttk.Frame(settings_frame)
        frame_input_folder.grid(row=2, column=1, padx=5, pady=5, sticky='ew')
        entry_input_folder = ttk.Entry(frame_input_folder, textvariable=self.input_base_folder)
        entry_input_folder.pack(side='left', padx=5, pady=5, fill='x', expand=True)
        btn_browse_input = ttk.Button(frame_input_folder, text="Durchsuchen", command=self.browse_input_folder)
        btn_browse_input.pack(side='left', padx=5, pady=5)

        lbl_output_folder = ttk.Label(settings_frame, text="Ausgabeordner:")
        lbl_output_folder.grid(row=3, column=0, padx=5, pady=5, sticky='w')
        frame_output_folder = ttk.Frame(settings_frame)
        frame_output_folder.grid(row=3, column=1, padx=5, pady=5, sticky='ew')
        entry_output_folder = ttk.Entry(frame_output_folder, textvariable=self.output_folder)
        entry_output_folder.pack(side='left', padx=5, pady=5, fill='x', expand=True)
        btn_browse_output = ttk.Button(frame_output_folder, text="Durchsuchen", command=self.browse_output_folder)
        btn_browse_output.pack(side='left', padx=5, pady=5)

        lbl_palette = ttk.Label(settings_frame, text="Farbpalette (optional):")
        lbl_palette.grid(row=4, column=0, padx=5, pady=5, sticky='w')
        entry_palette = ttk.Entry(settings_frame, textvariable=self.palette)
        entry_palette.grid(row=4, column=1, padx=5, pady=5, sticky='ew')

        lbl_gpl_file = ttk.Label(settings_frame, text="GIMP Palette (.gpl) Datei:")
        lbl_gpl_file.grid(row=5, column=0, padx=5, pady=5, sticky='w')
        frame_gpl = ttk.Frame(settings_frame)
        frame_gpl.grid(row=5, column=1, padx=5, pady=5, sticky='ew')
        entry_gpl = ttk.Entry(frame_gpl, textvariable=self.gpl_file_path)
        entry_gpl.pack(side='left', padx=5, pady=5, fill='x', expand=True)
        btn_browse_gpl = ttk.Button(frame_gpl, text="Durchsuchen", command=self.browse_gpl_file)
        btn_browse_gpl.pack(side='left', padx=5, pady=5)

        # Einstellungen für Detailgrad und Glättung
        lbl_line_fit_tolerance = ttk.Label(settings_frame, text="Standard Detailgrad (line_fit_tolerance):")
        lbl_line_fit_tolerance.grid(row=6, column=0, padx=5, pady=5, sticky='w')

        entry_line_fit_tolerance = ttk.Entry(settings_frame, textvariable=self.line_fit_tolerance)
        entry_line_fit_tolerance.grid(row=6, column=1, padx=5, pady=5, sticky='ew')

        lbl_anti_aliasing_mode = ttk.Label(settings_frame, text="Standard Glättung (anti_aliasing_mode):")
        lbl_anti_aliasing_mode.grid(row=7, column=0, padx=5, pady=5, sticky='w')

        combo_anti_aliasing_mode = ttk.Combobox(settings_frame, textvariable=self.anti_aliasing_mode, values=['anti_aliased', 'aliased'])
        combo_anti_aliasing_mode.grid(row=7, column=1, padx=5, pady=5, sticky='ew')
        combo_anti_aliasing_mode.current(0)  # Standardwert: 'anti_aliased'

        # Eingabe- und Ausgabe-DPI in den Einstellungen
        lbl_input_dpi = ttk.Label(settings_frame, text="Input DPI:")
        lbl_input_dpi.grid(row=8, column=0, padx=5, pady=5, sticky='w')
        entry_input_dpi = ttk.Entry(settings_frame, textvariable=self.input_dpi)
        entry_input_dpi.grid(row=8, column=1, padx=5, pady=5, sticky='ew')

        lbl_output_dpi = ttk.Label(settings_frame, text="Output DPI:")
        lbl_output_dpi.grid(row=9, column=0, padx=5, pady=5, sticky='w')
        entry_output_dpi = ttk.Entry(settings_frame, textvariable=self.output_dpi)
        entry_output_dpi.grid(row=9, column=1, padx=5, pady=5, sticky='ew')

        # Button zum Speichern der Einstellungen
        btn_save_settings = ttk.Button(settings_frame, text="Einstellungen speichern", command=self.save_settings)
        btn_save_settings.grid(row=10, column=0, columnspan=2, pady=20)
        settings_frame.columnconfigure(1, weight=1)

    def browse_input_folder(self):
        folder_path = filedialog.askdirectory()
        if folder_path:
            self.input_base_folder.set(folder_path)

    def browse_output_folder(self):
        folder_path = filedialog.askdirectory()
        if folder_path:
            self.output_folder.set(folder_path)

    def browse_gpl_file(self):
        file_path = filedialog.askopenfilename(filetypes=[("GIMP Palette Dateien", "*.gpl")])
        if file_path:
            self.gpl_file_path.set(file_path)

    def load_settings(self):
        if os.path.exists(self.config_file):
            self.config.read(self.config_file)
            if 'API' in self.config:
                self.api_key.set(self.config['API'].get('api_key', ''))
                self.api_secret.set(self.config['API'].get('api_secret', ''))
            if 'Settings' in self.config:
                self.input_base_folder.set(self.config['Settings'].get('input_base_folder', ''))
                self.output_folder.set(self.config['Settings'].get('output_folder', ''))
                self.palette.set(self.config['Settings'].get('palette', ''))
                self.mode.set(self.config['Settings'].get('mode', 'test'))
                self.output_format.set(self.config['Settings'].get('output.file_format', 'png'))
                self.gpl_file_path.set(self.config['Settings'].get('gpl_file_path', ''))
                # Neue Einstellungen laden
                self.line_fit_tolerance.set(self.config['Settings'].get('line_fit_tolerance', '0.1'))
                self.anti_aliasing_mode.set(self.config['Settings'].get('anti_aliasing_mode', 'anti_aliased'))
                self.input_dpi.set(self.config['Settings'].get('input_dpi', '96'))
                self.output_dpi.set(self.config['Settings'].get('output_dpi', '96'))
                self.max_colors.set(self.config['Settings'].get('processing.max_colors', '36'))  # Standardwert auf 36 gesetzt
                self.min_area_px.set(self.config['Settings'].get('processing.shapes.min_area_px', '50'))  # Einstellungen laden
        else:
            # Standardwerte setzen
            self.line_fit_tolerance.set('0.1')
            self.anti_aliasing_mode.set('anti_aliased')
            self.input_dpi.set('96')
            self.output_dpi.set('96')
            self.max_colors.set('36')  # Standardwert auf 36 gesetzt
            self.min_area_px.set('50')  # Standardwert setzen
        logging.info("Einstellungen geladen.")

    def save_settings(self):
        self.config['API'] = {
            'api_key': self.api_key.get(),
            'api_secret': self.api_secret.get()
        }
        self.config['Settings'] = {
            'input_base_folder': self.input_base_folder.get(),
            'output_folder': self.output_folder.get(),
            'palette': self.palette.get(),
            'mode': self.mode.get(),
            'output.file_format': self.output_format.get(),
            'gpl_file_path': self.gpl_file_path.get(),
            # Neue Einstellungen speichern
            'line_fit_tolerance': self.line_fit_tolerance.get(),
            'anti_aliasing_mode': self.anti_aliasing_mode.get(),
            'input_dpi': self.input_dpi.get(),
            'output_dpi': self.output_dpi.get(),
            'processing.max_colors': self.max_colors.get(),  # Neue Einstellung speichern
            'processing.shapes.min_area_px': self.min_area_px.get()  # Einstellungen speichern
        }
        try:
            with open(self.config_file, 'w', encoding='utf-8') as configfile:
                self.config.write(configfile)
            messagebox.showinfo("Einstellungen gespeichert", "Die Einstellungen wurden erfolgreich gespeichert.")
            logging.info("Einstellungen gespeichert.")
        except Exception as e:
            messagebox.showerror("Fehler", f"Fehler beim Speichern der Einstellungen:\n{e}")
            logging.error(f"Fehler beim Speichern der Einstellungen: {e}")

    def on_closing(self):
        if messagebox.askyesno("Beenden", "Möchten Sie das Programm wirklich beenden?"):
            logging.info("VectorizerApp wird beendet.")
            self.destroy()

    def on_mode_change(self, *args):
        current_mode = self.mode.get()
        logging.debug(f"Modus geändert zu: {current_mode}")

        if current_mode == 'preview':
            # Ausgabeformat auf 'png' setzen und Radiobuttons entsprechend deaktivieren
            self.output_format.set('png')
            if 'svg' in self.rb_output_formats:
                self.rb_output_formats['svg'].configure(state='disabled')
            logging.info("Modus ist 'preview'. Ausgabeformat auf 'png' gesetzt und 'svg' deaktiviert.")
        else:
            # Radiobuttons wieder aktivieren
            if 'svg' in self.rb_output_formats:
                self.rb_output_formats['svg'].configure(state='normal')
            logging.info(f"Modus ist '{current_mode}'. Ausgabeformat-Radiobuttons wieder aktiviert.")

if __name__ == '__main__':
    app = VectorizerApp()
    app.protocol("WM_DELETE_WINDOW", app.on_closing)
    app.mainloop()
