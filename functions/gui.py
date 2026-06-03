import matplotlib.pyplot as plt
from matplotlib.colors import Colormap
from nicegui import ui
import sounddevice as sd
import yaml
from .config import DIALOGS_CONFIG_PATH


def _load_dialogs_config():
    """Load dialog text from dialogs.yaml configuration file.
    
    Reads the dialogs configuration file and extracts the 'dialogs' section
    for use by GUI components like ErrorDialog, SettingsScreen, and other
    dialog classes.
    
    Returns:
        dict: Dictionary containing dialog configurations indexed by dialog type,
              e.g. {'error_dialog': {...}, 'end_screen': {...}, etc.}
    """
    with open(DIALOGS_CONFIG_PATH, 'r', encoding="utf-8") as file:
        config = yaml.safe_load(file)
    return config.get('dialogs', {})


# Load dialog configuration once on module import
_dialogs_config = _load_dialogs_config()


class ErrorDialog(ui.dialog):
    """Dialog displaying missing stimulus files error."""
    def __init__(self, missing_files: list[str]):
        """Initialize error dialog with list of missing files.
        
        Args:
            missing_files: List of missing stimulus file paths to display
        """
        super().__init__()
        self.props('persistent')
        
        files_str = '\n'.join([f'  - {f}' for f in missing_files])
        
        with self, ui.card().style('margin: auto; position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%);'):
            with ui.column().style('align-items: center; gap: 1em;'):
                ui.label('⚠️ Measurement Setup Failed').style('font-size: 1.2em; font-weight: bold;')
                ui.label(files_str).style('white-space: pre-wrap; color: #d32f2f; font-family: monospace;')
                ui.label('Please verify the measurement list file and ensure all stimulus files exist.').style('color: #666;')
                ui.button('OK', on_click=self.close).style('margin-top: 0.5em;')


class SettingsScreen(ui.dialog):
    def __init__(
            self,
            device_list: sd.DeviceList,
            device_supported_fs: dict,
            blocksize_init: int = 256,
            fs_preferred: list[int] | None = None):
        """Initialize a settings dialog for audio device configuration.
        
        Creates a persistent modal dialog allowing users to select audio output device,
        sampling rate, and blocksize. This is the base class for measurement-specific
        settings screens.
        
        Args:
            device_list: List of available sound devices from sounddevice
            device_supported_fs: Dictionary mapping device indices to their supported sampling rates
            blocksize_init: Initial blocksize value in samples (default: 256)
            fs_preferred: List of preferred sampling frequencies in descending priority order.
                         If provided, the first available frequency in this list will be selected
                         for each device. If None or empty, the highest available frequency is used.
        """
        super().__init__()
        self.props('persistent')
        self.device_list = device_list
        self.device_supported_fs = device_supported_fs
        self.blocksize_init = blocksize_init
        self.fs_preferred = fs_preferred

        self.idx_list = [d['index'] for d in self.device_list]
        self.selection_list = [f"{d['index']}: {d['name']}" for d in self.device_list]
        default_out = self.idx_list[0] if self.idx_list else None

        with self, ui.card().style('margin: auto; position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%);'):
            with ui.column().style('display: flex; align-items: center; justify-content: center;'):
                self._build_extra_fields()  # hook: subclass fields inserted first
                self._build_device_fields(default_out)
                self.submit_btn = ui.button('Submit', on_click=self.submit)

    def _select_fs_from_available(self, available_fs_list: list[int]) -> str:
        """Select sampling frequency from available options based on preference list.
        
        Args:
            available_fs_list: List of available sampling frequencies (integers)
        
        Returns:
            Formatted string like "48000 Hz" for dropdown use
        """
        if not available_fs_list:
            return ''
        
        # If no preference is set or it's empty, use the highest available frequency
        if not self.fs_preferred:
            selected_fs = available_fs_list[-1]  # Highest frequency
        else:
            # Try to find the first fs in the preference list that's available
            selected_fs = None
            for preferred_fs in self.fs_preferred:
                if preferred_fs in available_fs_list:
                    selected_fs = preferred_fs
                    break
            # If no preference matched, fall back to highest available
            if selected_fs is None:
                selected_fs = available_fs_list[-1]
        
        return f'{selected_fs} Hz'

    def _build_extra_fields(self):
        """Hook for subclasses to inject additional fields before device settings."""
        pass

    def _build_device_fields(self, default_out):
        """Build device, sampling rate and blocksize fields."""
        if self.selection_list:
            def update_fs_options():
                selected_device_id = self.idx_list[self.selection_list.index(self.dropdown_device.value)]
                available_fs_list = self.device_supported_fs.get(selected_device_id, [])
                new_fs_labels = [f'{fs} Hz' for fs in available_fs_list]
                self.dropdown_fs.set_options(new_fs_labels)
                if new_fs_labels:
                    selected_fs_label = self._select_fs_from_available(available_fs_list)
                    self.dropdown_fs.set_value(selected_fs_label)

            self.dropdown_device = ui.select(
                self.selection_list,
                value=self.selection_list[self.idx_list.index(default_out)] if default_out is not None else self.selection_list[0],
                label='Audio Device',
                on_change=update_fs_options
            ).style('width: 100%;')

            default_fs_list = self.device_supported_fs.get(default_out if default_out is not None else self.idx_list[0], [])
            fs_labels = [f'{fs} Hz' for fs in default_fs_list]
            initial_fs_value = self._select_fs_from_available(default_fs_list) if default_fs_list else ''
            self.dropdown_fs = ui.select(
                fs_labels,
                value=initial_fs_value,
                label='Sampling Rate (fs)'
            ).style('width: 100%;')
        else:
            self.dropdown_device = None
            self.dropdown_fs = None
            ui.label('No stereo output devices found').classes('text-warning')

        self.blocksize_textfield = ui.input(
            label='Blocksize', value=str(self.blocksize_init)
        ).style('width: 100%;')

    def _collect_settings(self) -> dict:
        """Collect base device settings. Override/extend in subclasses."""
        fs_value = int(self.dropdown_fs.value.split()[0]) if self.dropdown_fs and self.dropdown_fs.value else 48000
        return {
            'device_id': self.idx_list[self.selection_list.index(self.dropdown_device.value)],
            'fs': fs_value,
            'blocksize': int(self.blocksize_textfield.value or self.blocksize_init)
        }

    def submit(self) -> None:
        """Collect settings and close dialog.
        
        Gathers device, sampling rate, and blocksize settings from UI fields,
        passes them to parent class submit handler, and closes the dialog.
        """
        super().submit(self._collect_settings())


class SettingsScreenMeasurement(SettingsScreen):
    """Settings dialog specialized for audio measurement experiments.
    
    Extends the base SettingsScreen with measurement-specific configuration fields:
    - Calibration selection with automatic device/fs pre-population
    - Participant ID input for identifying study subjects
    - Stimulus list selection for choosing the measurement list
    - Device availability validation with error messaging
    
    The collected settings include all base device settings plus the additional
    measurement parameters (participant_id, stimulus_list, calibration_filename).
    """
    def __init__(
            self,
            txt_file_list: list[str],
            device_list: sd.DeviceList,
            device_supported_fs: dict,
            calibrations: list[dict] = None,
            blocksize_init: int = 256):
        """Initialize measurement settings dialog with stimulus list and calibration options.
        
        Args:
            txt_file_list: List of available stimulus list file names to choose from
            device_list: List of available sound devices from sounddevice
            device_supported_fs: Dictionary mapping device indices to their supported sampling rates
            calibrations: List of calibration metadata dicts with keys:
                         filename, device_id, device_name, fs, timestamp_str
            blocksize_init: Initial blocksize value in samples (default: 256)
        """
        self.txt_file_list = txt_file_list  # must be set before super().__init__ calls _build_extra_fields
        self.calibrations = calibrations or []
        self.valid_device_ids = [d['index'] for d in device_list]
        self.initial_calib_display = None  # Store for validation after super().__init__
        super().__init__(device_list, device_supported_fs, blocksize_init)
        
        # Lock device and fs dropdown (chosen by selected calibration)
        self.dropdown_device.enabled = False
        self.dropdown_fs.enabled = False

        self.submit_btn.enabled = False # enabled, if valid calibration found

        # Perform initial calibration validation after button is created
        if self.calibrations and self.dropdown_calibration and self.initial_calib_display:
            self._validate_calibration(self.initial_calib_display)

    def _build_extra_fields(self):
        """Add calibration, participant ID, and stimulus list fields."""
        # Calibration selector with device availability check
        if self.calibrations:
            # Create reliable mapping from display string to calibration dict
            calib_display_list = [self._format_calibration_display(c) for c in self.calibrations]
            self._calib_by_display = {display: calib for display, calib in zip(calib_display_list, self.calibrations)}
            self.initial_calib_display = calib_display_list[0]
            
            self.dropdown_calibration = ui.select(
                calib_display_list,
                value=calib_display_list[0],
                label='Calibration',
                on_change=self._on_calibration_change
            ).style('width: 100%;')
            
            # Error message for device availability (hidden by default)
            self.error_message = ui.label('').classes('text-warning')
        else:
            self.dropdown_calibration = None
            self._calib_by_display = {}
            self.error_message = ui.label('No calibrations found').classes('text-warning')
        
        # Participant ID field
        self.participant_id_field = ui.input(
            label='Participant ID', value='VP001'
        ).style('width: 100%;')

        # Stimulus list field
        if self.txt_file_list:
            self.dropdown_filelist = ui.select(
                self.txt_file_list,
                value=self.txt_file_list[0],
                label='Stimulus List'
            ).style('width: 100%;')
        else:
            self.dropdown_filelist = None
            ui.label('No stimulus lists found in directory').classes('text-warning')

    def _on_calibration_change(self, event):
        """When calibration is selected, check device availability and pre-populate fields."""
        # Get the actual value from the dropdown (on_change passes event, not value)
        calibration_display = self.dropdown_calibration.value
        self._validate_calibration(calibration_display)

    def _validate_calibration(self, calibration_display: str):
        """Validate calibration and update UI state based on device availability.
        
        Args:
            calibration_display: Display string of selected calibration
        """
        # Reliably get calibration from mapping
        selected_calib = self._calib_by_display.get(calibration_display)
        
        device_id = selected_calib['device_id']
        
        # Device is available: enable submit and pre-populate device/fs
        self.submit_btn.enabled = True
        self.error_message.set_text('')
        
        # Find device display string
        device_display = next(
            (f"{d['index']}: {d['name']}" for d in self.device_list if d['index'] == device_id),
            None
        )
        
        if device_display:
            # Set device (on_change callback will update fs options)
            self.dropdown_device.set_value(device_display)
            fs_display = f"{selected_calib['fs']} Hz"
            self.dropdown_fs.set_value(fs_display)

    def _format_calibration_display(self, calib: dict) -> str:
        """Format calibration metadata for display in dropdown.
        
        Args:
            calib: Calibration metadata dict
            
        Returns:
            Formatted string like "Realtek Audio (48000 Hz) — 2026-05-28 13:26"
        """
        timestamp = calib['timestamp_str']  # e.g., "2026-05-28T13-26-08"
        # Convert to readable format: "2026-05-28 13:26"
        readable_timestamp = timestamp.replace('T', ' ').rsplit('-', 1)[0]
        return f"{calib['device_name']} ({calib['fs']} Hz) — {readable_timestamp}"

    def _collect_settings(self) -> dict:
        settings = super()._collect_settings()
        
        # Extract calibration filename from dropdown value using reliable mapping
        calib_filename = None
        if self.dropdown_calibration:
            calib_display = self.dropdown_calibration.value
            selected_calib = self._calib_by_display.get(calib_display)
            if selected_calib:
                calib_filename = selected_calib['filename']
        
        settings.update({
            'participant_id': self.participant_id_field.value,
            'stimulus_list': self.dropdown_filelist.value if self.dropdown_filelist else None,
            'calibration_filename': calib_filename,
        })
        return settings

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
        """Initialize the end screen dialog to display completion message.
        
        Creates a modal dialog that appears when the measurement session is
        completed. The dialog displays a completion message from the dialogs
        configuration file and is persistent (cannot be dismissed by clicking
        outside the dialog). Used to inform the user that the experiment has
        concluded and thank them for their participation.
        """
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
    def value(self) -> float:
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
        invert_cmap: bool = False) -> tuple[int, int, int]:
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