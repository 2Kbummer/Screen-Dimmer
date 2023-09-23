"""
screen_dimmer.py
-----------------------------------
Summary:
    This project allows users to change the brightness of their monitor(s).
    This project uses PySimpleGUI as the gui. When closing window, will hide in system Tray. To quit press 'Exit' button
    You can control each individual monitor's brightness with a slider with a range from 0-100% brightness
    A OFF/ON button is added to disable sliders & make brightness %100
    Also uses pynput for hotkey support which is 'Alt + z' to press OFF/ON button while minimized or in system tray
"""

import PySimpleGUI as Sg  # gui
import screen_brightness_control as sbc  # brightness control
from psgtray import SystemTray  # system tray
import threading  # for hotkey
from pynput.keyboard import GlobalHotKeys
import webbrowser  # for url

ICON = 'favicon.ico'
GIT_URL = 'https://github.com/2Kbummer'


def main():
    # TODO: extras - save/load preset brightness, config file, github file structure

    text_color = ['Yellow', 'Orange', 'Blue', 'Black', 'Purple', 'Pink', 'Red']  # text color for monitor text that will be displayed
    url_font = ('Arial', 10, 'underline')
    Sg.change_look_and_feel('DarkTeal')  # theme for pysimplegui; look up theme names online

    monitor_count, monitor_names, current_monitors_brightness, monitor_brightness_keys, monitor_text_keys, monitor_text_list = keys_and_lists()

    menu = ['',
            ['Turn Off/On', '---', 'Show Window', 'Hide Window', 'Exit']]
    layout = [
        [Sg.Text('source @2kbummer github', key='github_link', text_color='Black', tooltip=GIT_URL, enable_events=True, font=url_font), Sg.Push(), Sg.Button('Exit', key='Exit')],
        [Sg.Text('Monitor Brightness Control', text_color='Dark Grey', font='BigFont')],
        [[[Sg.Text(monitor_text_list[i], key=monitor_text_keys[i], text_color=text_color[i])], [Sg.Slider(key=monitor_brightness_keys[i], orientation='horizontal', range=(0, 100), default_value=current_monitors_brightness[i], size=(100, 25), enable_events=True)]] for i in range(monitor_count)],
        [Sg.Button('OFF/ON', key='off_on_button', tooltip='HotKey: Alt + z')]
    ]

    # Create the window
    window = Sg.Window('Screen Dimmer', layout, icon=ICON, resizable=True, element_justification='c', size=(350, 350), finalize=True, enable_close_attempted_event=True)  # Window Definition
    window.bind("<Alt><z>", 'off_on_button')  # pressing alt + z, presses 'off_on' button

    # function for hotkey listener to add it to 'target' argument in threading.Thread for syntax reasons
    def hotkey_press_listener():
        with GlobalHotKeys({'<alt>+z': lambda key='Hotkey': window.write_event_value(key, None)}) as listener:
            listener.join()

    # Thread for hotkey listener
    threading.Thread(target=hotkey_press_listener, daemon=True).start()

    tooltip = 'Screen Dimmer'  # will show when hovering over icon in system tray
    tray = SystemTray(menu, single_click_events=False, window=window, icon=ICON, tooltip=tooltip)

    brightness_values_list = []  # list of brightness values grabbed from slider in real time
    final_brightness_text_list = []  # list of monitor text that is displayed when moving slider in real time
    disable_count = 0  # keeps track of amount of 'OFF/ON' button presses
    while True:
        event, values = window.read()  # can use window.read(timeout=5000) to make window reset after 5000ms
        if event == tray.key:
            event = values[event]  # use the System Tray's event as if was from the window
        if event in (Sg.WIN_CLOSED, 'Exit'):
            break  # breaks while loop
        if event == 'github_link':
            webbrowser.open(GIT_URL)
        if event in ('Show Window', Sg.EVENT_SYSTEM_TRAY_ICON_DOUBLE_CLICKED):  # when in-tray, the 'show window' option or double-clicking icon will shows window
            window.un_hide()
            window.bring_to_front()
        elif event in ('Hide Window', Sg.WIN_CLOSE_ATTEMPTED_EVENT):  # when in-tray, the 'hide window' option or closing window hides window
            window.hide()
            tray.show_icon()  # if hiding window, better make sure the icon is visible

        # disabling button logic: every odd number of presses disables slider & makes brightness 100
        if event in ('off_on_button', 'Turn Off/On', 'Hotkey'):
            disable_count += 1
        if disable_count % 2 == 1:  # num % 2 = 0 is even
            disable_brightness = True
        else:
            disable_brightness = False

        # logic that changes brightness when moving slider & updates text
        if not disable_brightness:
            for i in range(monitor_count):
                if len(brightness_values_list) == monitor_count:  # since constant adding of brightness values to list, need to 'reset' when length is more than monitor count
                    brightness_values_list = []
                    final_brightness_text_list = []
                window.Element(monitor_brightness_keys[i]).update(disabled=False)  # if 'off/on' button pressed it disables slider, so needs a reset to make it active again
                brightness_values_list.append(values[monitor_brightness_keys[i]])  # values[] = making dictionary
                final_brightness_text_list.append(f'Monitor {i + 1}: {monitor_names[i]} : {brightness_values_list[i]} %')
                window[monitor_text_keys[i]].update(final_brightness_text_list[i])  # updating displayed monitor text
                sbc.set_brightness(values[monitor_brightness_keys[i]], display=i)  # setting brightness to slider values

        # logic that makes brightness 100% & disables slider when event to disable brightness triggered
        elif disable_brightness:
            for k in range(monitor_count):
                sbc.set_brightness(100, display=k)
                window.Element(monitor_brightness_keys[k]).update(disabled=True)  # disables slider movement

    tray.close()
    window.close()


def keys_and_lists():
    monitor_text_list = []  # list of the monitor texts that will be displayed; ex. "Monitor 1: ASUS-MAX56991 : 100%"
    monitor_text_keys = []  # list of keys of the monitor text; keys are used to identify the text (like an id)
    monitor_brightness_keys = []  # list of keys for the slider which gives us the value we want; ex. move slider to 50, then brightness will be 50
    current_monitors_brightness = []  # list of current brightness from sbc.get_brightness (actual monitor brightness)
    monitor_names = []  # list of the monitor names; ex. ASUS-MAX56991
    monitor_count = 0
    i = 0
    for monitor in sbc.list_monitors():
        monitor_names.append(monitor)  # grabs monitor name from sbc.list_monitor
        try:
            current_monitors_brightness.append(
                *(sbc.get_brightness(display=monitor)))  # adds current brightness to empty list; * unpacks list
        except ScreenBrightnessError:  # if sbc cant identify brightness of monitor breaks loops to avoid error
            continue  # breaks loop to start next iteration
        monitor_status = f'Monitor {i + 1}: {monitor_names[i]} : {sbc.get_brightness(display=monitor)} %'  # text that will be displayed on top of slider
        monitor_text_list.append(monitor_status)
        monitor_text_keys.append(f'monitor{i}_text')  # key for text
        monitor_brightness_keys.append(f'monitor{i}_brightness')  # key for slider
        monitor_count += 1
        i += 1
    return monitor_count, monitor_names, current_monitors_brightness, monitor_brightness_keys, monitor_text_keys, monitor_text_list


if __name__ == '__main__':
    main()
