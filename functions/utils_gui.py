from nicegui import ui
import os
import sounddevice as sd

ALPHA = 0.3
RGB_MAX = 255

def get_color_from_colormap(value: float, val_min: float, val_max: float, better_at_high: bool = True) -> str:
    """ Returns RGB values for setting the GUI background color.
    Uses a red ↔ green gradient where:
    - Red indicates "bad" values
    - Orange/Yellow indicates middle values
    - Green indicates "good" values

    Args:
        value (float):  Current value
        val_min (float): Minimum value
        val_max (float): Maximum value
        better_at_high (bool): If True, higher values are better (green at max).
                               If False, lower values are better (green at min).

    Returns:
        str: String containing RGB values to be passed to nicegui component
    """
    # Normalize the value between 0 and 1
    normalized_value = (value - val_min) / (val_max - val_min)
    normalized_value = max(0.0, min(1.0, normalized_value))  # Clamp to [0, 1]
    
    # If higher is better, invert so that normalized_value maps: good → high
    if better_at_high:
        normalized_value = 1.0 - normalized_value
    
    # Now normalized_value represents "goodness": 0 = bad (red), 1 = good (green)
    # Create a red→orange→yellow→green gradient
    # Red: RGB(255, 0, 0) → Orange: RGB(255, 165, 0) → Green: RGB(0, 200, 0)
    
    if normalized_value < 0.5:
        # Red to Orange: 0→0.5 maps to red→orange
        f = normalized_value * 2  # 0 to 1
        r = int(255)
        g = int(165 * f)  # 0 to 165 (creating orange)
        b = int(0)
    else:
        # Orange to Green: 0.5→1 maps to orange→green
        f = (normalized_value - 0.5) * 2  # 0 to 1
        r = int(255 * (1 - f))  # 255 to 0
        g = int(165 + (35 * f))  # 165 to 200 (creating yellow-green to green)
        b = int(0)
    
    # Add alpha blending for a softer appearance
    r = int(r + ((RGB_MAX - r) * ALPHA))
    g = int(g + ((RGB_MAX - g) * ALPHA))
    b = int(b + ((RGB_MAX - b) * ALPHA))
    
    return f'rgb({r}, {g}, {b})'

class Vertical_Slider(ui.slider):
    def __init__(self, min_val:float, max_val:float, step_width:float,
            value_init:float, marker_step:float, use_full_container:bool=True
            ):
        """ Constructor
        Extends a usual ui.slider to a vertical one.

        Args:
            min_val (float):    Minimum value on slider
            max_val (float):    Maximum value on slider
            step_width (float): Delta between values on slider
            value_init (float): Value, where slider is first positioned on init
            marker_step (float):Steps between marker lines on the slider
            use_full_container (bool, optional):Allows for filling up whole
                                container. Defaults to True.
        """
        super().__init__(min=min_val, max=max_val, step=step_width, value=value_init)
        self.props(
            "vertical selection-color=transparent track-size='2rem' thumb-size='4rem' "
            f":markers='{marker_step}' "
        )
        if use_full_container:
            self.classes("h-full my-2")
    
    def set_range(self, min_val: float, max_val: float):
        """Set min and max values for slider.
        
        Note: NiceGUI sliders cannot change min/max after initialization.
        This method is a no-op; configure the slider at creation time.
        
        Args:
            min_val: Minimum value (ignored - slider range is fixed)
            max_val: Maximum value (ignored - slider range is fixed)
        """
        pass  # NiceGUI sliders cannot change range after initialization
    
    def set_value(self, value: float):
        """Set slider value.
        
        Args:
            value: Value to set
        """
        self.value = value
    
    def enable(self):
        """Enable slider interaction."""
        self.enabled = True
    
    def disable(self):
        """Disable slider interaction."""
        self.enabled = False

def make_labels(label_dict: dict):
    """ Small function to make a column of all Listening Effort categories provided """
    le_vals = sorted(label_dict.keys(), reverse=True)
    for val in le_vals:
        label = label_dict[val]
        if label=="":
            ui.space()
        else:
            ui.label(label).classes('text-xs')

class StartDialog(ui.dialog):
    def __init__(self, function_handle):
        """ Allowing the user to press 'Start' once ready, which executes e.g. audio playback"""
        super().__init__()
        self.props('persistent')
        self.function_handle = function_handle

        # Build the UI inside the dialog
        with self, ui.card().style('margin: auto; position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%);'):
            with ui.row().classes('w-full justify-center'):
                ui.label('Drücken Sie "Start", wenn Sie die Kopfhörer aufgesetzt haben und bereit sind!')
            with ui.row().classes('w-full justify-center'):
                ui.button('Start', on_click=self.start_button_clicked)

    def start_button_clicked(self):
        self.close()
        self.function_handle()

class GreetingsDialog(ui.dialog):
    def __init__(self, start_dialog: StartDialog):
        """ Allowing the user to press 'Start' once ready, which executes e.g. audio playback"""
        super().__init__()
        self.props('persistent')
        self.start_dialog = start_dialog

        # Build the UI inside the dialog
        with self, ui.card().style('margin: auto; position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%);'):
            with ui.row().classes('w-full justify-center'):
                ui.label('Willkommen zu unserer Hörstudie. Wenn Sie den Instruktionsbogen gelesen haben, '+\
                    'drücken Sie bitte auf "Beginnen"! Vor jedem Abschnitt öffnet sich ein Fenster, '+\
                    'in dem sie durch drücken von "Start" das Abspielen des Audios beginnen könenen.')
            with ui.row().classes('w-full justify-center'):
                ui.button('Beginnen', on_click=self.start_button_clicked)

    def start_button_clicked(self):
        self.close()
        self.start_dialog.open()

class PostStimulusDialog(ui.dialog):
    def __init__(self, function_handle):
        """ Reminding the user to answer the questions after each chapter 
        
        Args:
            chapter (int).  Current chapter, which will be refered to in the
                            dialog. If value is 0, it will be assumed that
                            the training chapter has been played back
        """
        super().__init__()
        self.props('persistent')
        self.function_handle = function_handle
        self._stimulus_name = ''

        # Build the UI inside the dialog
        with self, ui.card().style('margin: auto; position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%);'):
            with ui.row().classes('w-full justify-center'):
                self.text_label = ui.label(
                    'Bitte beantworten Sie die Fragen auf dem Fragebogen! '+\
                    'Drücken Sie "Weiter", wenn Sie alle Fragen beantwortet haben!'
                    )
            with ui.row().classes('w-full justify-center'):
                ui.button('Weiter', on_click=self.continue_button_clicked)
        
    @property
    def stimulus_file(self):
        return self._stimulus_name

    @stimulus_file.setter
    def stimulus_file(self, filepath):
        self._stimulus_name = filepath

    def continue_button_clicked(self):
        self.close()
        self.function_handle()

class EndScreen(ui.dialog):
    def __init__(self):
        """ Small end screen for informing the user """
        super().__init__()
        self.props('persistent')

        with self, ui.card().style('margin: auto; position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%);'):
            with ui.row().classes('w-full justify-center'):
                ui.label('Sie haben den Hörversuch abgeschlossen. Vielen Dank für Ihre Teilnahme!')

class SettingsScreen(ui.dialog):
    def __init__(
            self,
            on_submit=None,
            initial_stimulus_list: str = 'measurement/Measurement_Lists',
            initial_output_dir: str = 'measurement/Results',
            initial_blocksize: int = 256,
            initial_buffersize: int = 4):
        """ Settings dialog for experiment configuration.
        
        Args:
            on_submit: Callback function on submit (receives all settings as kwargs)
            initial_stimulus_list: Default stimulus list path
            initial_output_dir: Default output directory
            initial_blocksize: Default blocksize
            initial_buffersize: Default buffersize
        """
        super().__init__()
        self.props('persistent')
        self.on_submit = on_submit
        self.initial_stimulus_list = initial_stimulus_list
        self.initial_output_dir = initial_output_dir
        self.initial_blocksize = initial_blocksize
        self.initial_buffersize = initial_buffersize

        # Looking for the measurement lists
        measurement_list_path = os.path.dirname(initial_stimulus_list) if os.path.isfile(initial_stimulus_list) else initial_stimulus_list
        if os.path.isdir(measurement_list_path):
            file_list_unsorted = [file for file in os.listdir(measurement_list_path) if '.txt' in file]
            self.file_list = sorted(file_list_unsorted, key=lambda x: int(x.split('List')[1].split('.')[0]) if 'List' in x and x[x.find('List')+4:].split('.')[0].isdigit() else float('inf'))
            self.filepath_list = [os.path.join(measurement_list_path, file) for file in self.file_list]
            default_file = self.file_list[0] if self.file_list else ''
        else:
            self.file_list = []
            self.filepath_list = []
            default_file = ''

        # Looking for all stereo output devices
        device_list = [d for d in sd.query_devices() if d['max_output_channels'] == 2]
        self.idx_list = [d['index'] for d in device_list]
        self.selection_list = [f"{d['index']}: {d['name']}" for d in device_list]
        default_out = self.idx_list[0] if self.idx_list else None

        # Build the UI inside the dialog
        with self, ui.card().style('margin: auto; position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%);'):
            with ui.column().style('display: flex; align-items: center; justify-content: center;'):
                self.participant_id_field = ui.input(
                    label='Participant ID', value='VP001'
                ).style('width: 100%;')
                
                if self.file_list:
                    self.dropdown_filelist = ui.select(
                        self.file_list,
                        value=default_file,
                        label='Stimulus List'
                    ).style('width: 100%;')
                else:
                    self.dropdown_filelist = None
                    ui.label('No stimulus lists found in directory').classes('text-warning')
                
                if self.selection_list:
                    self.dropdown_device = ui.select(
                        self.selection_list,
                        value=self.selection_list[self.idx_list.index(default_out)] if default_out is not None else self.selection_list[0],
                        label='Audio Device'
                    ).style('width: 100%;')
                else:
                    self.dropdown_device = None
                    ui.label('No stereo output devices found').classes('text-warning')
                
                with ui.row():
                    self.blocksize_textfield = ui.input(
                        label='Blocksize', value=str(initial_blocksize)
                    )
                    self.blocksize_textfield.tooltip('Block size for audio processing')
                    
                    self.buffersize_textfield = ui.input(
                        label='Buffersize', value=str(initial_buffersize)
                    )
                    self.buffersize_textfield.tooltip('Buffer size for audio')
                
                with ui.row():
                    self.language_select = ui.select(
                        ['de', 'en'],
                        value='de',
                        label='Language'
                    )
                
                ui.button('Submit', on_click=self.submit)

    def submit(self):
        """Collect settings and call on_submit callback."""
        if not self.on_submit:
            self.close()
            return
        
        # Get stimulus list filepath
        if self.dropdown_filelist and self.file_list:
            selected_file = self.dropdown_filelist.value
            stimulus_list = self.filepath_list[self.file_list.index(selected_file)]
        else:
            stimulus_list = self.initial_stimulus_list
        
        # Get device ID
        if self.dropdown_device and self.selection_list:
            selected_device = self.dropdown_device.value
            device_id = self.idx_list[self.selection_list.index(selected_device)]
        else:
            device_id = None
        
        # Collect settings
        settings = {
            'participant_id': self.participant_id_field.value,
            'stimulus_list': stimulus_list,
            'output_dir': self.initial_output_dir,
            'device_id': device_id,
            'blocksize': int(self.blocksize_textfield.value or self.initial_blocksize),
            'buffersize': int(self.buffersize_textfield.value or self.initial_buffersize),
            'language': self.language_select.value if hasattr(self, 'language_select') else 'de',
        }
        
        # Close dialog
        self.close()
        
        # Call callback
        self.on_submit(**settings)