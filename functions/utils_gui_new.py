import matplotlib.pyplot as plt
from nicegui import ui
import sounddevice as sd

class SettingsScreen(ui.dialog):
    def __init__(
            self,
            txt_file_list: list[str],
            device_list: sd.DeviceList,
            # stimuli_lists_path: str = 'txt_lists_debugging',
            results_path: str = 'measurement/Results',
            blocksize_init: int = 256,
            buffersize_init: int = 4):
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
        self.txt_file_list = txt_file_list
        self.device_list = device_list
        self.results_path = results_path
        self.blocksize_init = blocksize_init
        self.buffersize_init = buffersize_init

        # Sound device
        self.idx_list = [d['index'] for d in self.device_list]
        self.selection_list = [f"{d['index']}: {d['name']}" for d in self.device_list]
        default_out = self.idx_list[0] if self.idx_list else None

        # Build the UI inside the dialog
        with self, ui.card().style('margin: auto; position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%);'):
            with ui.column().style('display: flex; align-items: center; justify-content: center;'):
                self.participant_id_field = ui.input(
                    label='Participant ID', value='VP001'
                ).style('width: 100%;')
                
                if self.txt_file_list:
                    self.dropdown_filelist = ui.select(
                        self.txt_file_list,
                        value=self.txt_file_list[0] if self.txt_file_list else '',
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
                        label='Blocksize', value=str(blocksize_init)
                    )
                    self.blocksize_textfield.tooltip('Block size for audio processing')
                    
                    self.buffersize_textfield = ui.input(
                        label='Buffersize', value=str(buffersize_init)
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
        settings = {
            'participant_id': self.participant_id_field.value,
            'stimulus_list': self.dropdown_filelist.value,
            'output_dir': self.results_path,
            'device_id': self.idx_list[self.selection_list.index(self.dropdown_device.value)],
            'blocksize': int(self.blocksize_textfield.value or self.blocksize_init),
            'buffersize': int(self.buffersize_textfield.value or self.buffersize_init),
            'language': self.language_select.value if hasattr(self, 'language_select') else 'de',
        }
        super().submit(settings)

class StartDialog(ui.dialog):
    def __init__(self):
        """ Allowing the user to press 'Start' once ready, which executes e.g. audio playback"""
        super().__init__()
        self.props('persistent')

        # Build the UI inside the dialog
        with self, ui.card().style('margin: auto; position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%);'):
            with ui.row().classes('w-full justify-center'):
                ui.label('Drücken Sie "Start", wenn Sie die Kopfhörer aufgesetzt haben und bereit sind!')
            with ui.row().classes('w-full justify-center'):
                ui.button('Start', on_click=self.submit)
    
    def submit(self):
        super().submit(True)

class PostStimulusDialog(ui.dialog):
    def __init__(self):
        """ Reminding the user to answer the questions after each chapter 
        
        Args:
            chapter (int).  Current chapter, which will be refered to in the
                            dialog. If value is 0, it will be assumed that
                            the training chapter has been played back
        """
        super().__init__()
        self.props('persistent')

        # Build the UI inside the dialog
        with self, ui.card().style('margin: auto; position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%);'):
            with ui.row().classes('w-full justify-center'):
                self.text_label = ui.label(
                    'Bitte beantworten Sie die Fragen auf dem Fragebogen! '+\
                    'Drücken Sie "Weiter", wenn Sie alle Fragen beantwortet haben!'
                    )
            with ui.row().classes('w-full justify-center'):
                ui.button('Weiter', on_click=self.submit)
    
    def submit(self):
        super().submit(True)

class EndScreen(ui.dialog):
    def __init__(self):
        """ Small end screen for informing the user """
        super().__init__()
        self.props('persistent')

        with self, ui.card().style('margin: auto; position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%);'):
            with ui.row().classes('w-full justify-center'):
                ui.label('Sie haben den Hörversuch abgeschlossen. Vielen Dank für Ihre Teilnahme!')

class RatingSlider(ui.column):
    def __init__(
            self,
            min_val:float = 1.0,
            max_val:float = 14.0,
            step_width:float = 0.1,
            value_init:float = 7.0,
            marker_step:float = 1.0,
            cmap_name:str = 'hsv',
            cmap_min: float = 0.03,
            cmap_max:float = 0.33,
            background_alpha:float = 0.5
            ):
        super().__init__()
        self._min_val = min_val
        self._max_val = max_val
        self._step_width = step_width
        self._value_init = value_init
        self._marker_step = marker_step
        self._cmap_name = cmap_name
        self._cmap_min = cmap_min
        self._cmap_max = cmap_max
        self._background_alpha = background_alpha

        self._cmap = plt.get_cmap(self._cmap_name)

        self._categories_dict = {
            1:  "mühelos",
            2:  "",
            3:  "sehr wenig anstrengend",
            4:  "",
            5:  "wenig anstrengend",
            6:  "",
            7:  "mittelgradig anstrengend",
            8:  "",
            9:  "deutlich anstrengend",
            10: "",
            11: "sehr anstrengend",
            12: "",
            13: "extrem anstrengend",
            14: "nur Störgeräusch"
        }
        
        with self.classes("w-full items-center"):
            ui.label('Le Slider!').classes("h-[10svh] text-3xl")
            
            with ui.row().classes("h-[90svh] max-h-96"):
                with ui.column().classes("h-full justify-center"):
                    self.slider = ui.slider(
                        min = self._min_val,
                        max = self._max_val,
                        step = self._step_width,
                        value = self._value_init
                    ).on('update:model-value', lambda e: self.update_background_color(e.args))
                    # TODO for general usage define reverse arg, if 1 should be at top and >1 at the bottom...
                    self.slider.props(
                        "vertical reverse selection-color=transparent track-size='2rem' thumb-size='4rem' "
                        f":markers='{self._marker_step}' "
                    )
                    self.slider.classes("h-full my-2")
                
                with ui.column().classes("h-full justify-between"):
                    le_vals = sorted(self._categories_dict.keys(), reverse=True)
                    for val in le_vals:
                        label = self._categories_dict[val]
                        if label=="":
                            ui.space()
                        else:
                            ui.label(label).classes('text-xs')
    
    @property
    def value(self):
        return self.slider.value
    
    def enable(self):
        self.slider.enable()
    
    def disable(self):
        self.slider.disable()

    def update_background_color(self, value: float):
        # TODO make separate testable function that also allows for colorizing "in the other direction" (1=red, 14=green)
        norm_val = (value - self._min_val) / (self._max_val - self._min_val)
        mapped_value = (1-norm_val) * (self._cmap_max - self._cmap_min) + self._cmap_min # TODO INVERSION! (1-norm_val)
        color = self._cmap(mapped_value)
        r, g, b = [int(c * 255) for c in color[:3]] # for RGB, 255 is the maximum value
        r += ((255 - r) * self._background_alpha)
        g += ((255 - g) * self._background_alpha)
        b += ((255 - b) * self._background_alpha)
        bg = f'rgb({r}, {g}, {b})'
        ui.query('body').style(f'background-color: {bg}')