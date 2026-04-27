import matplotlib.pyplot as plt
from matplotlib.colors import Colormap
from nicegui import ui
import sounddevice as sd
import yaml
from .config import DIALOGS_CONFIG_PATH


def _load_dialogs_config():
    """Load dialog text from dialogs.yaml configuration file."""
    with open(DIALOGS_CONFIG_PATH, 'r', encoding="utf-8") as file:
        config = yaml.safe_load(file)
    return config.get('dialogs', {})


# Load dialog configuration once on module import
_dialogs_config = _load_dialogs_config()


class SettingsScreen(ui.dialog):
    def __init__(
            self,
            txt_file_list: list[str],
            device_list: sd.DeviceList,
            # stimuli_lists_path: str = 'txt_lists_debugging',
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
                    
                ui.button('Submit', on_click=self.submit)

    def submit(self):
        """Collect settings and call on_submit callback."""
        settings = {
            'participant_id': self.participant_id_field.value,
            'stimulus_list': self.dropdown_filelist.value,
            'device_id': self.idx_list[self.selection_list.index(self.dropdown_device.value)],
            'blocksize': int(self.blocksize_textfield.value or self.blocksize_init)
        }
        super().submit(settings)

class StartDialog(ui.dialog):
    def __init__(self):
        """Dialog allowing user to start audio playback once ready."""
        super().__init__()
        self.props('persistent')

        config = _dialogs_config.get('start_dialog', {})
        text = config.get('text', 'Start')
        button_label = config.get('button', 'Start')

        # Build the UI inside the dialog
        with self, ui.card().style('margin: auto; position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%);'):
            with ui.row().classes('w-full justify-center'):
                ui.label(text)
            with ui.row().classes('w-full justify-center'):
                ui.button(button_label, on_click=self.submit)
    
    def submit(self):
        """Submit dialog and proceed to audio playback."""
        super().submit(True)

class PostStimulusDialog(ui.dialog):
    def __init__(self):
        """Dialog reminding user to answer questions after each stimulus."""
        super().__init__()
        self.props('persistent')

        config = _dialogs_config.get('post_stimulus_dialog', {})
        text = config.get('text', 'Please answer the questionnaire.')
        button_label = config.get('button', 'Next')

        # Build the UI inside the dialog
        with self, ui.card().style('margin: auto; position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%);'):
            with ui.row().classes('w-full justify-center'):
                self.text_label = ui.label(text)
            with ui.row().classes('w-full justify-center'):
                ui.button(button_label, on_click=self.submit)
    
    def submit(self):
        """Submit dialog and proceed to next stimulus."""
        super().submit(True)

class EndScreen(ui.dialog):
    def __init__(self):
        """ Small end screen for informing the user """
        super().__init__()
        self.props('persistent')

        config = _dialogs_config.get('end_screen', {})
        text = config.get('text', 'Experiment completed. Thank you for your participation!')

        with self, ui.card().style('margin: auto; position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%);'):
            with ui.row().classes('w-full justify-center'):
                ui.label(text)

class RatingSlider(ui.column):
    def __init__(
            self,
            min_val:float = 1.0,
            max_val:float = 14.0,
            init_val:float = 7.0,
            step_width:float = 0.1,
            title:str = 'Listening Effort',
            categories_dict:dict = {
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
            },
            marker_step:float = 1.0,
            cmap_name:str = 'hsv',
            cmap_min: float = 0.03,
            cmap_max:float = 0.33,
            invert_cmap: bool = True,
            background_alpha:float = 0.5,
            set_enabled_on_init:bool = False
            ):
        """Initialize a rating slider UI component with customizable appearance and behavior.
        
        Args:
            min_val: Minimum slider value
            max_val: Maximum slider value
            init_val: Initial slider value
            step_width: Step size for slider increments
            title: Title displayed above the slider
            categories_dict: Dictionary mapping values to category labels
            marker_step: Step size for slider markers
            cmap_name: Matplotlib colormap name for background color
            cmap_min: Minimum value for colormap range
            cmap_max: Maximum value for colormap range
            invert_cmap: Whether to invert the colormap
            background_alpha: Alpha transparency for background color
            set_enabled_on_init: Whether to enable slider on initialization
        """
        super().__init__()
        self._min_val = min_val
        self._max_val = max_val
        self._init_val = init_val
        self._step_width = step_width
        self._title = title
        self._categories_dict = categories_dict
        self._marker_step = marker_step
        self._cmap_name = cmap_name
        self._cmap_min = cmap_min
        self._cmap_max = cmap_max
        self._invert_cmap = invert_cmap
        self._background_alpha = background_alpha
        self._set_enabled_on_init = set_enabled_on_init

        self._cmap = plt.get_cmap(self._cmap_name)

        
        with self.classes("w-full items-center"):
            ui.label(self._title).classes("h-[10svh] text-3xl")
            
            with ui.row().classes("h-[90svh] max-h-96"):
                with ui.column().classes("h-full justify-center"):
                    self.slider = ui.slider(
                        min = self._min_val,
                        max = self._max_val,
                        step = self._step_width,
                        value = self._init_val
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
            
        if not self._set_enabled_on_init:
            self.disable()
    
    @property
    def value(self):
        """Get the current slider value."""
        return self.slider.value
    
    def enable(self):
        """Enable the slider for user interaction."""
        self.slider.enable()
    
    def disable(self):
        """Disable the slider to prevent user interaction."""
        self.slider.disable()

    def update_background_color(self, value: float):
        """Update page background color based on slider value.
        
        Args:
            value: Current slider value to map to color
        """
        r, g, b = get_rbg_colors(
            cmap = self._cmap,
            value = value,
            min_val = self._min_val,
            max_val = self._max_val,
            cmap_min = self._cmap_min,
            cmap_max = self._cmap_max,
            alpha = self._background_alpha,
            invert_cmap = self._invert_cmap
        )
        ui.query('body').style(f'background-color: rgb({r}, {g}, {b})')

def get_rbg_colors(
        cmap: Colormap,
        value: float,
        min_val: float,
        max_val: float,
        cmap_min: float,
        cmap_max: float,
        alpha: float,
        invert_cmap: bool = False):
    """Map a value to RGB color using a matplotlib colormap.
    
    Args:
        cmap: Matplotlib colormap to use
        value: Value to map to color
        min_val: Minimum value in range
        max_val: Maximum value in range
        cmap_min: Minimum colormap parameter
        cmap_max: Maximum colormap parameter
        alpha: Transparency alpha value (0-1)
        invert_cmap: Whether to invert the colormap
        
    Returns:
        Tuple of (R, G, B) color values (0-255)
    """
    if invert_cmap:
        norm_val = (value - max_val) / (min_val - max_val)
    else:
        norm_val = (value - min_val) / (max_val - min_val)
    mapped_value = norm_val * (cmap_max - cmap_min) + cmap_min
    color = cmap(mapped_value)
    r, g, b = [int(255 * (c * (1 - alpha) + alpha)) for c in color[:3]]
    return r, g, b