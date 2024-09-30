import pyvisa
import tkinter as tk
from tkinter import ttk
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import numpy as np
import pygame

class WF1973ControlApp:
    def __init__(self, root):
        self.root = root
        self.root.title("WF1973 Control Panel")
        self.root.geometry("1200x800")

        self.style = ttk.Style()
        self.style.theme_use("clam")

        self.rm = pyvisa.ResourceManager()
        self.instrument = None

        self.waveform_mapping = {
            "SIN": "SIN",
            "SQUARE": "SQU",
            "PULSE": "PULS",
            "RAMP": "RAMP",
            "NOISE": "NOIS",
            "DC": "DC"
        }

        pygame.mixer.init()
        self.click_sound = pygame.mixer.Sound("click.mp3")

        self.create_widgets()

    def play_click_sound(self):
        self.click_sound.play()

    def create_widgets(self):
        # Main frame
        main_frame = ttk.Frame(self.root, padding="10 10 10 10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)

        # Connection controls
        connection_frame = ttk.LabelFrame(main_frame, text="Connection")
        connection_frame.grid(row=0, column=0, padx=5, pady=5, sticky=(tk.W, tk.E))

        self.instruments = self.rm.list_resources()
        self.selected_instrument = tk.StringVar()
        
        ttk.Label(connection_frame, text="Select Instrument:").grid(row=0, column=0, sticky=tk.W)
        self.instrument_dropdown = ttk.Combobox(connection_frame, textvariable=self.selected_instrument, values=self.instruments)
        self.instrument_dropdown.grid(row=0, column=1, sticky=(tk.W, tk.E))

        ttk.Button(connection_frame, text="Connect", command=lambda: [self.play_click_sound(), self.connect()]).grid(row=0, column=2, padx=5)
        ttk.Button(connection_frame, text="Disconnect", command=lambda: [self.play_click_sound(), self.disconnect()]).grid(row=0, column=3, padx=5)
        ttk.Button(connection_frame, text="Get IDN", command=lambda: [self.play_click_sound(), self.get_idn()]).grid(row=0, column=4, padx=5)

        # Waveform controls
        waveform_frame = ttk.LabelFrame(main_frame, text="Waveform Control")
        waveform_frame.grid(row=1, column=0, padx=5, pady=5, sticky=(tk.W, tk.E))

        self.waveform = tk.StringVar()
        self.waveform.trace_add("write", self.update_parameters)
        ttk.Label(waveform_frame, text="Waveform:").grid(row=0, column=0, sticky=tk.W)
        ttk.Combobox(waveform_frame, textvariable=self.waveform, values=list(self.waveform_mapping.keys())).grid(row=0, column=1, sticky=(tk.W, tk.E))
        ttk.Button(waveform_frame, text="Set Waveform", command=lambda: [self.play_click_sound(), self.set_waveform()]).grid(row=0, column=2, padx=5)

        # Dynamic parameter controls
        self.parameter_frames = {}
        parameter_frame = ttk.Frame(main_frame)
        parameter_frame.grid(row=2, column=0, padx=5, pady=5, sticky=(tk.W, tk.E))

        self.create_parameter_frame(parameter_frame, "freq", "Frequency (Hz)", 1, "entry")
        self.create_parameter_frame(parameter_frame, "aptd", "Amplitude (V)", 2, "entry")
        self.create_parameter_frame(parameter_frame, "offset", "Offset (V)", 3, "entry")
        self.create_parameter_frame(parameter_frame, "phase", "Phase (Degrees)", 4, "entry")
        self.create_parameter_frame(parameter_frame, "duty", "Duty Cycle (%)", 5, "entry")
        self.create_parameter_frame(parameter_frame, "symm", "Symmetry", 6, "entry")

        # Output controls
        output_frame = ttk.LabelFrame(main_frame, text="Output Control")
        output_frame.grid(row=3, column=0, padx=5, pady=5, sticky=(tk.W, tk.E))
        ttk.Button(output_frame, text="Enable Output", command=lambda: [self.play_click_sound(), self.enable_output()]).grid(row=0, column=0, padx=5)
        ttk.Button(output_frame, text="Disable Output", command=lambda: [self.play_click_sound(), self.disable_output()]).grid(row=0, column=1, padx=5)

        # Status display
        status_frame = ttk.LabelFrame(main_frame, text="Status")
        status_frame.grid(row=4, column=0, padx=5, pady=5, sticky=(tk.W, tk.E))
        self.status = tk.StringVar()
        self.status.set("Disconnected")
        ttk.Label(status_frame, textvariable=self.status).grid(row=0, column=0, sticky=tk.W)

        # Set Parameters Button
        ttk.Button(main_frame, text="Set Parameters", command=lambda: [self.play_click_sound(), self.set_parameters()]).grid(row=5, column=0, padx=5, pady=5, sticky=(tk.W, tk.E))

        # Graph display
        graph_frame = ttk.LabelFrame(main_frame, text="Waveform Graph")
        graph_frame.grid(row=0, column=1, rowspan=7, padx=5, pady=5, sticky=(tk.N, tk.S, tk.W))
        self.figure, self.ax = plt.subplots(figsize=(3.5, 3))  # Adjust the figsize to make the graph smaller
        self.canvas = FigureCanvasTkAgg(self.figure, master=graph_frame)
        self.canvas.get_tk_widget().grid(row=0, column=0, padx=10, pady=10, sticky=(tk.W))

        # Sliders for adjusting the scale
        slider_frame = ttk.Frame(graph_frame)
        slider_frame.grid(row=1, column=0, pady=5, sticky=(tk.W, tk.E))
        ttk.Label(slider_frame, text="X Scale (micro to hundred):").grid(row=0, column=0, sticky=tk.W)
        self.x_scale = tk.DoubleVar(value=1.0)
        self.x_slider = ttk.Scale(slider_frame, from_=0.000001, to=100.0, orient=tk.HORIZONTAL, variable=self.x_scale, length=300, command=self.update_graph)
        self.x_slider.grid(row=0, column=1, sticky=(tk.W, tk.E))

        ttk.Label(slider_frame, text="Y Scale (micro to hundred):").grid(row=1, column=0, sticky=tk.W)
        self.y_scale = tk.DoubleVar(value=10.0)
        self.y_slider = ttk.Scale(slider_frame, from_=0.000001, to=100.0, orient=tk.HORIZONTAL, variable=self.y_scale, length=300, command=self.update_graph)
        self.y_slider.grid(row=1, column=1, sticky=(tk.W, tk.E))

        ttk.Button(graph_frame, text="Predict Graph", command=lambda: [self.play_click_sound(), self.predict_graph()]).grid(row=2, column=0, pady=5)

        for child in main_frame.winfo_children():
            child.grid_configure(padx=5, pady=5)

    def create_parameter_frame(self, parent, param_name, label, row, control_type="entry", options=None):
        frame = ttk.Frame(parent)
        frame.grid(row=row, column=0, columnspan=2, sticky=(tk.W, tk.E))
        
        label_widget = ttk.Label(frame, text=f"{label}:")
        label_widget.grid(row=0, column=0, sticky=tk.W, padx=(0, 5))
        entry_widget = None
        if control_type == "entry":
            var = tk.DoubleVar()
            entry_widget = ttk.Entry(frame, textvariable=var)
            entry_widget.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=(0, 5))
            entry_widget.config(width=20)  # Set the width of the entry boxes to be consistent
        setattr(self, param_name, var)
        setattr(self, f"{param_name}_frame", frame)
        self.parameter_frames[param_name] = frame

        parent.grid_columnconfigure(1, weight=1)

    def connect(self):
        try:
            resource = self.selected_instrument.get()
            self.instrument = self.rm.open_resource(resource)
            self.status.set("Connected: " + self.instrument.query('*IDN?'))
        except Exception as e:
            self.status.set(f"Connection failed: {e}")

    def disconnect(self):
        if self.instrument:
            self.instrument.close()
            self.instrument = None
        self.status.set("Disconnected")

    def get_idn(self):
        if self.instrument:
            try:
                idn = self.instrument.query('*IDN?')
                self.status.set(f"IDN: {idn}")
            except Exception as e:
                self.status.set(f"Failed to get IDN: {e}")

    def set_waveform(self):
        if self.instrument:
            waveform = self.waveform.get()
            instrument_waveform = self.waveform_mapping[waveform]
            self.instrument.write(f'FUNC {instrument_waveform}')
            current_waveform = self.instrument.query('FUNC?').strip()
            if current_waveform == instrument_waveform:
                self.status.set(f"Waveform set to {waveform}")
            else:
                self.status.set(f"Failed to set waveform to {waveform}, current waveform is {current_waveform}")

    def set_parameters(self):
        if self.instrument:
            # Set frequency
            if self.freq.get():
                self.instrument.write(f'FREQ {self.freq.get()}')
            # Set amplitude
            if self.aptd.get():
                self.instrument.write(f'VOLT {self.aptd.get()}')
            # Set offset
            if self.offset.get():
                self.instrument.write(f'VOLT:OFFSET {self.offset.get()}')
            # Set phase
            if self.phase.get():
                self.instrument.write(f'PHAS {self.phase.get()}')
            # Set duty cycle 
            if self.duty.get() and self.waveform.get() == "SQUARE":
                self.instrument.write(f'FUNC:SQU:DCYC {self.duty.get()}')
            # Set symmetry 
            if self.symm.get() and self.waveform.get() == "RAMP":
                self.instrument.write(f'FUNC:RAMP:SYMMetry {self.symm.get()}')
            self.status.set("Parameters set")

    def enable_output(self):
        if self.instrument:
            self.instrument.write('OUTP ON')
            self.status.set("Output enabled")

    def disable_output(self):
        if self.instrument:
            self.instrument.write('OUTP OFF')
            self.status.set("Output disabled")

    def update_parameters(self, *args):
        waveform = self.waveform.get()
        
        # Hide all parameter frames initially
        for frame in self.parameter_frames.values():
            frame.grid_remove()

        # Show relevant parameter frames based on waveform type
        if waveform in ["SIN", "SQUARE", "PULSE", "RAMP"]:
            self.parameter_frames["freq"].grid(sticky=(tk.W, tk.E))
            self.parameter_frames["aptd"].grid(sticky=(tk.W, tk.E))
            self.parameter_frames["offset"].grid(sticky=(tk.W, tk.E))
            self.parameter_frames["phase"].grid(sticky=(tk.W, tk.E))

            if waveform == "SQUARE":
                self.parameter_frames["duty"].grid(sticky=(tk.W, tk.E))
            elif waveform == "RAMP":
                self.parameter_frames["symm"].grid(sticky=(tk.W, tk.E))
        
        elif waveform == "NOISE":
            self.parameter_frames["aptd"].grid(sticky=(tk.W, tk.E))
            self.parameter_frames["offset"].grid(sticky=(tk.W, tk.E))
        
        elif waveform == "DC":
            self.parameter_frames["offset"].grid(sticky=(tk.W, tk.E))

    def predict_graph(self):
        waveform = self.waveform.get()
        freq = self.freq.get() if self.freq.get() else 1
        amp = self.aptd.get() if self.aptd.get() else 1
        offset = self.offset.get() if self.offset.get() else 0
        phase = self.phase.get() if self.phase.get() else 0

        t = np.linspace(-10, 10, 10000)  # Adjusted to show a longer time span for continuous display
        y = np.zeros_like(t)

        if waveform == "SIN":
            y = amp * np.sin(2 * np.pi * freq * t + np.deg2rad(phase)) + offset
        elif waveform == "SQUARE":
            y = amp * np.sign(np.sin(2 * np.pi * freq * t + np.deg2rad(phase))) + offset
        elif waveform == "PULSE":
            y = amp * (np.sin(2 * np.pi * freq * t + np.deg2rad(phase)) > 0).astype(float) + offset
        elif waveform == "RAMP":
            y = amp * (2 * (t * freq - np.floor(1/2 + t * freq))) + offset
        elif waveform == "NOISE":
            y = amp * np.random.normal(size=t) + offset
        elif waveform == "DC":
            y = np.full_like(t, offset)

        self.ax.clear()
        self.ax.plot(t, y)
        self.ax.set_title(f'{waveform} Waveform')
        self.ax.set_xlabel('Time')
        self.ax.set_ylabel('Amplitude')
        self.update_graph()
        self.canvas.draw()

    def update_graph(self, event=None):
        self.ax.set_xlim(-self.x_scale.get(), self.x_scale.get())
        self.ax.set_ylim(-self.y_scale.get(), self.y_scale.get())
        self.canvas.draw()
