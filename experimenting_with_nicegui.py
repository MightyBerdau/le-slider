from nicegui import ui

async def run_experiment():
    with ui.dialog() as start_dialog, ui.card():
        ui.label('Willkommen')
        ui.button('Start', on_click=lambda: start_dialog.submit('start'))
    await start_dialog

    ratings = []
    audio_files = ['a.wav', 'b.wav', 'c.wav']

    for i, f in enumerate(audio_files):
        label = ui.label(f'Abschnitt {i+1}')
        slider = ui.slider(min=0, max=100, value=50)

        with ui.dialog() as pause_dialog, ui.card():
            ui.button('Weiter', on_click=lambda: pause_dialog.submit('weiter'))
        await pause_dialog

        ratings.append(slider.value)
        label.delete()
        slider.delete()
        pause_dialog.delete()

    ui.label('Fertig!')

ui.timer(0, run_experiment, once=True)  # startet sobald die UI bereit ist

ui.run(host='0.0.0.0')