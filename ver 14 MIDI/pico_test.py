import usb_cdc, board, displayio, busio, gc, rotaryio
import time, analogio, asyncio, digitalio, terminalio
from ulab.numpy import interp
import usb_hid, usb_midi, adafruit_midi
from adafruit_midi.control_change import ControlChange
from adafruit_hid.keyboard import Keyboard
from adafruit_hid.Keycode import Keycode as KC
from adafruit_hid.consumer_control import ConsumerControl
from adafruit_hid.consumer_control_code import ConsumerControlCode as CC
from adafruit_display_text import label
import adafruit_displayio_ssd1306
import adafruit_ds1307
from adafruit_debouncer import Debouncer
import json


def get_correct_keycode(key_name):
    if hasattr(KC, key_name):
        return getattr(KC, key_name)
    if hasattr(CC, key_name):
        return getattr(CC, key_name)
    return None

# Constants
DISPLAY_WIDTH = 128
DISPLAY_HEIGHT = 64
DISPLAY_ADDRESS = 0x3C

# Page Types
PAGE_CLOCK = "CLOCK"
PAGE_MEDIA = "MEDIA"
PAGE_LAYOUT = "LAYOUTS"
MIDI_CONTROLLER_NAME = "MIDI CONTROLLER"


class DisplayManager:
    def __init__(self, sda, scl, rtc_manager, configfile_manager, macropad_manager):
        self.i2c = busio.I2C(scl, sda)
        self.display = self._init_display()

        self.rtc_manager = rtc_manager
        self.configfile_manager = configfile_manager
        self.macropad_manager = macropad_manager

        self.encoder_position = None
        self.main_title = "No Media"
        self.sub_title = "currently playing"
        self.is_media_title_changed = False
        self.display_width = 128
        self.display_height = 64

        self.previous_min = 0
        self.is_min_changed = False

        self.clock_click = False
        self.layout_click = False

        # Handle for the files. TO store the last visited page and then load it.

        self.last_visited_page = self.configfile_manager.get("last_page")
        self.current_page = self.last_visited_page

        # layout page handler
        self.last_layout = self.configfile_manager.get("last_layout")
        self.layout_names = self.configfile_manager.keyboard_layouts_names()
        self.layout_names.append(MIDI_CONTROLLER_NAME)
        self.layout_index = self.layout_names.index(self.last_layout)


    def _init_display(self):
        displayio.release_displays()
        display_bus = displayio.I2CDisplay(self.i2c, device_address=DISPLAY_ADDRESS)
        return adafruit_displayio_ssd1306.SSD1306(
            display_bus, width=DISPLAY_WIDTH, height=DISPLAY_HEIGHT)

    async def display_last_page(self):
        if self.last_visited_page == PAGE_CLOCK:
            await self.clock_page()

        elif self.last_visited_page == PAGE_MEDIA:
            self.media_page()

        elif self.last_visited_page == PAGE_LAYOUT:
            await self.layout_page()

    def _create_base_group(self):
        splash = displayio.Group()
        background = self._create_background()
        splash.append(background)
        return splash

    def _create_background(self):
        bitmap = displayio.Bitmap(DISPLAY_WIDTH, DISPLAY_HEIGHT, 1)
        palette = displayio.Palette(1)
        palette[0] = 0  # Black
        return displayio.TileGrid(bitmap, pixel_shader=palette, x=0, y=0)

    def media_page(self):
        splash = self._create_base_group()

        # Get display width
        display_width = self.display_width

        # Add labels
        labels = [
            # {"text": "MEDIA", "y": 5},
            {"text": self.main_title[:21], "y": 10},
            {"text": self.main_title[21:42], "y": 25},
            {"text": self.main_title[42:63], "y": 40},
            {"text": self.sub_title[:21], "y": 55}
        ]

        for label_info in labels:
            text_label = label.Label(
                terminalio.FONT,
                text=label_info["text"],
                color=0xFFFFFF
            )
            # Center-align text
            text_label.x = (display_width - text_label.bounding_box[2]) // 2
            text_label.y = label_info["y"]

            splash.append(text_label)

        self.display.root_group = splash
        self.current_page = PAGE_MEDIA

    async def clock_page(self):
        # Create reusable palettes
        white_palette = displayio.Palette(1)
        white_palette[0] = 0xFFFFFF

        black_palette = displayio.Palette(1)
        black_palette[0] = 0x000000

        def create_scroll_indicator(width, height, x, y):
            """Create a fresh scroll indicator with its own bitmap and palette"""
            bitmap = displayio.Bitmap(width, height, 1)
            # Fill the bitmap completely
            for i in range(width):
                for j in range(height):
                    bitmap[i, j] = 0  # Set all pixels to the first color in the palette

            # Start with black by default
            indicator = displayio.TileGrid(bitmap, pixel_shader=black_palette, x=x, y=y)
            return indicator

        # Helper function to get days in a month, accounting for leap years
        def days_in_month(month, year):
            if month in [4, 6, 9, 11]:
                return 30
            elif month == 2:
                # Check for leap year
                is_leap = (year % 4 == 0 and year % 100 != 0) or (year % 400 == 0)
                return 29 if is_leap else 28
            else:
                return 31

        # Helper function to get day of week from date
        def get_day_of_week(day, month, year):
            # Zeller's Congruence algorithm to find day of week
            if month < 3:
                month += 12
                year -= 1

            k = year % 100
            j = year // 100

            day_of_week = (day + 13 * (month + 1) // 5 + k + k // 4 + j // 4 - 2 * j) % 7

            # Convert from Zeller's result (0=Saturday) to standard weekday (0=Monday)
            day_of_week = (day_of_week + 5) % 7

            return day_of_week

        # Create base display group
        splash = self._create_base_group()

        # Create all indicators with their positions
        hr_scroll = create_scroll_indicator(49, 37, 3, 15)
        min_scroll = create_scroll_indicator(49, 37, 74, 15)
        year_scroll = create_scroll_indicator(26, 16, 69, 54)
        mon_scroll = create_scroll_indicator(14, 16, 32, 54)
        dt_scroll = create_scroll_indicator(14, 16, 51, 54)


        # Add indicators to the display group
        splash.append(hr_scroll)
        splash.append(min_scroll)
        splash.append(year_scroll)
        splash.append(mon_scroll)
        splash.append(dt_scroll)

        # Get display width
        display_width = self.display_width

        # Get current time data
        hour, minute, date, month, year, day = self.rtc_manager.current_time()
        clock_text = f"{hour:02d}:{minute:02d}"
        date_text = f"{date:02d}/{month:02d}/{year:02d}"

        # Add clock elements
        elements = [
            {"text": clock_text, "y": 33, "scale": 4},  # Larger clock
            {"text": day, "y": 5, "scale": 1},  # Normal size day
            {"text": date_text, "y": 59, "scale": 1}  # Normal size date
        ]

        text_labels = []

        for element in elements:
            text_label = label.Label(
                terminalio.FONT,
                text=element["text"],
                color=0xFFFFFF,
                scale=element["scale"]  # Apply scaling
            )
            # Center-align text based on scaled width
            text_label.x = (display_width - text_label.bounding_box[2] * element["scale"]) // 2
            text_label.y = element["y"]

            splash.append(text_label)
            text_labels.append(text_label)

        # Set the display's root group
        self.display.root_group = splash
        self.current_page = PAGE_CLOCK

        # Handle settings mode
        if self.clock_click:
            # Store all indicators in a list for easier management
            indicators = [hr_scroll, min_scroll, year_scroll, dt_scroll, mon_scroll]

            # Update all indicators to black initially
            for indicator in indicators:
                indicator.pixel_shader = black_palette

            # Start with position -1 (no indicator selected)
            position = -1
            total_positions = len(indicators)

            # Keep text labels white in settings mode (changed from previous version)
            text_labels[0].color = 0xFFFFFF
            text_labels[1].color = 0xFFFFFF
            text_labels[2].color = 0xFFFFFF

            while True:
                if self.encoder_position is not None:
                    if self.encoder_position == "ONCLICK":
                        # Reset previous selection color
                        if 0 <= position < total_positions:
                            # Reset previously selected value's color to white
                            if position == 0 or position == 1:
                                text_labels[0].color = 0xFFFFFF
                            elif position >= 2:
                                text_labels[2].color = 0xFFFFFF

                            # Reset indicator to black
                            indicators[position].pixel_shader = black_palette

                        # Increment position (cycle through all positions)
                        position += 1

                        # Check if we need to exit
                        if position >= total_positions:
                            # Reset all indicators to black and ensure all text is white
                            for indicator in indicators:
                                indicator.pixel_shader = black_palette

                            text_labels[0].color = 0xFFFFFF
                            text_labels[1].color = 0xFFFFFF
                            text_labels[2].color = 0xFFFFFF

                            # Exit the settings mode
                            self.clock_click = False
                            self.encoder_position = None
                            print("Exiting clock settings page")

                            # Update the display one last time before exiting
                            self.display.root_group = splash
                            break

                        # Highlight current position indicator
                        indicators[position].pixel_shader = white_palette

                        # Invert selected value's color to black
                        if position == 0 or position == 1:
                            text_labels[0].color = 0x000000
                        elif position >= 2:
                            text_labels[2].color = 0x000000

                        # Handle adjustments based on position
                        if position == 0:
                            print("Adjusting hour")
                        elif position == 1:
                            print("Adjusting minute")
                        elif position == 2:
                            print("Adjusting date")
                        elif position == 3:
                            print("Adjusting month")
                        elif position == 4:
                            print("Adjusting year")

                    # Handle adjustment with PREV/NEXT when a position is selected
                    elif (
                            self.encoder_position == "PREV" or self.encoder_position == "NEXT") and 0 <= position < total_positions:
                        # These will be used for adjusting the selected value
                        adjustment = 1 if self.encoder_position == "PREV" else -1

                        # Adjust values based on current position
                        if position == 0:
                            # Adjust hour
                            hour = (hour + adjustment) % 24
                            # Update display
                            clock_text = f"{hour:02d}:{minute:02d}"
                            text_labels[0].text = clock_text
                            text_labels[0].x = (display_width - text_labels[0].bounding_box[2] * 4) // 2
                            # Keep the text color black to show it's selected
                            text_labels[0].color = 0x000000

                        elif position == 1:
                            # Adjust minute
                            minute = (minute + adjustment) % 60
                            # Update display
                            clock_text = f"{hour:02d}:{minute:02d}"
                            text_labels[0].text = clock_text
                            text_labels[0].x = (display_width - text_labels[0].bounding_box[2] * 4) // 2
                            # Keep the text color black to show it's selected
                            text_labels[0].color = 0x000000

                        elif position == 2:
                            # Adjust year (keep it reasonable)
                            year = max(2000, min(2150, year + adjustment))

                            # Validate day after year change (for leap years)
                            max_days = days_in_month(month, year)
                            if date > max_days:
                                date = max_days

                            # Update display
                            date_text = f"{date:02d}/{month:02d}/{year:02d}"
                            text_labels[2].text = date_text
                            text_labels[2].x = (display_width - text_labels[2].bounding_box[2]) // 2
                            # Keep the text color black to show it's selected
                            text_labels[2].color = 0x000000

                            # Automatically update the day of week
                            day_index = get_day_of_week(date, month, year)
                            day = self.rtc_manager.days[day_index]
                            text_labels[1].text = day
                            text_labels[1].x = (display_width - text_labels[1].bounding_box[2]) // 2

                        elif position == 3:
                            # Adjust month with validation
                            if adjustment > 0:
                                month = month + 1 if month < 12 else 1
                            else:
                                month = month - 1 if month > 1 else 12

                            # Validate day after month change
                            max_days = days_in_month(month, year)
                            if date > max_days:
                                date = max_days

                            # Update display
                            date_text = f"{date:02d}/{month:02d}/{year:02d}"
                            text_labels[2].text = date_text
                            text_labels[2].x = (display_width - text_labels[2].bounding_box[2]) // 2
                            # Keep the text color black to show it's selected
                            text_labels[2].color = 0x000000

                            # Automatically update the day of week
                            day_index = get_day_of_week(date, month, year)
                            day = self.rtc_manager.days[day_index]
                            text_labels[1].text = day
                            text_labels[1].x = (display_width - text_labels[1].bounding_box[2]) // 2

                        elif position == 4:
                            # Adjust date (day of month) with validation
                            max_days = days_in_month(month, year)

                            if adjustment > 0:
                                date = date + 1 if date < max_days else 1
                            else:
                                date = date - 1 if date > 1 else max_days

                            # Update display
                            date_text = f"{date:02d}/{month:02d}/{year:02d}"
                            text_labels[2].text = date_text
                            text_labels[2].x = (display_width - text_labels[2].bounding_box[2]) // 2
                            # Keep the text color black to show it's selected
                            text_labels[2].color = 0x000000

                            # Automatically update the day of week
                            day_index = get_day_of_week(date, month, year)
                            day = self.rtc_manager.days[day_index]
                            text_labels[1].text = day
                            text_labels[1].x = (display_width - text_labels[1].bounding_box[2]) // 2


                        # Update RTC with new values
                        day_index = get_day_of_week(date, month, year)
                        self.rtc_manager.set_time(hour, minute, date, month, year, week_day=day_index)

                    self.encoder_position = None

                await asyncio.sleep(0.1)

    async def layout_page(self):
        white_palette = displayio.Palette(1)
        white_palette[0] = 0xFFFFFF

        black_palette = displayio.Palette(1)
        black_palette[0] = 0x000000

        def create_scroll_indicator(width, height, x, y):
            """Create a fresh scroll indicator with its own bitmap and palette"""
            bitmap = displayio.Bitmap(width, height, 1)
            # Fill the bitmap completely
            for i in range(width):
                for j in range(height):
                    bitmap[i, j] = 0  # Set all pixels to the first color in the palette

            # Start with black by default
            indicator = displayio.TileGrid(bitmap, pixel_shader=black_palette, x=x, y=y)
            return indicator

        # Create base display group
        splash = self._create_base_group()

        # Create all indicators with their positions
        layout_scroll = create_scroll_indicator(128, 30, 0, 25)

        # Add indicators to the display group
        splash.append(layout_scroll)

        # Get display width
        display_width = self.display_width

        lyt_text = "Layouts"

        # Add clock elements
        elements = [
            {"text": lyt_text, "y": 10, "scale": 1},  # Normal size date
            {"text": self.layout_names[self.layout_index], "y": 40, "scale": 1}
        ]

        text_labels = []

        for element in elements:
            text_label = label.Label(
                terminalio.FONT,
                text=element["text"],
                color=0xFFFFFF,
                scale=element["scale"]  # Apply scaling
            )
            # Center-align text based on scaled width
            text_label.x = (display_width - text_label.bounding_box[2] * element["scale"]) // 2
            text_label.y = element["y"]

            splash.append(text_label)
            text_labels.append(text_label)

        # Set the display's root group
        self.display.root_group = splash
        self.current_page = PAGE_LAYOUT

        if self.layout_click:
            self.encoder_position = ""

            text_labels[1].color = 0x000000

            layout_scroll.pixel_shader = white_palette

            while True:

                if self.encoder_position is not None:

                    if self.encoder_position == "PREV":
                        if self.layout_index < len(self.layout_names) - 1:
                            self.layout_index += 1

                    elif self.encoder_position == "NEXT":
                        if self.layout_index > 0:
                            self.layout_index -= 1

                    elif self.encoder_position == "ONCLICK":
                        self.layout_click = False

                        text_labels[1].color = 0xFFFFFF
                        layout_scroll.pixel_shader = black_palette
                        self.encoder_position = None

                        self.last_layout = self.layout_names[self.layout_index]
                        
                        if self.last_layout != MIDI_CONTROLLER_NAME:

                            current_layout = (self.configfile_manager.
                                              keyboard_layout_values(self.layout_index, self.last_layout))
                            self.macropad_manager.update_keyboard_layout(current_layout[0])
                            self.macropad_manager.update_rotary_layout(current_layout[1])
                            self.macropad_manager.current_layout = self.last_layout
                        
                        else:
                            self.macropad_manager.current_layout = MIDI_CONTROLLER_NAME

                        self.configfile_manager.set("last_layout", self.last_layout)
                        self.configfile_manager.save()

                        break

                    self.encoder_position = None

                    text_labels[1].text = self.layout_names[self.layout_index]
                    text_labels[1].x = (display_width - text_labels[1].bounding_box[2]) // 2
                    # text_labels[1].y = 40

                await asyncio.sleep(0.1)


            self.layout_click = False



    async def update_display(self):
        while True:
            try:
                if self.clock_click or self.layout_click:
                    await asyncio.sleep(0.1)
                    continue

                if self.encoder_position in ["NEXT", "PREV"]:
                    await self._change_page(self.encoder_position)

                elif self.encoder_position == "ONCLICK":
                    if self.current_page == PAGE_CLOCK:
                        self.clock_click = True  # determines that the user clicked on the settings
                        print("Clock click detected!")  # Debug print
                        await self.clock_page()

                    elif self.current_page == PAGE_LAYOUT:
                        self.layout_click = True
                        print("Layout click detected!")
                        await self.layout_page()

                    else:
                        self.encoder_position = None

                elif self.current_page == PAGE_MEDIA and self.is_media_title_changed:
                    self.media_page()
                    self.is_media_title_changed = False
                    self.encoder_position = None

                elif (self.current_page == PAGE_CLOCK and self.is_min_changed and
                      not self.clock_click):
                    await self.clock_page()
                    self.is_min_changed = False
                    self.encoder_position = None

                await asyncio.sleep(0.1)
            except Exception as e:
                print(f"Display update error: {e}")
                await asyncio.sleep(1)

    def update_last_visited_page(self):
        self.configfile_manager.set("last_page", self.current_page)
        self.configfile_manager.save()

    async def check_curr_time(self):
        while True:
            _, minute, _, _, _, _ = self.rtc_manager.current_time()
            # print(f"RTC Minute: {minute}, Previous: {self.previous_min}")  # Debug print

            if minute != self.previous_min:
                self.previous_min = minute
                self.is_min_changed = True
                # print("Minute changed! Triggering display update.")  # Debug print

            await asyncio.sleep(5)

    async def _change_page(self, position):
        # IDK why but the NEXT and previous tags are inverted
        # So I changed the polarity here
        if self.current_page == PAGE_CLOCK:
            if position == "PREV":
                self.media_page()

            elif position == "NEXT":
                await self.layout_page()
            self.encoder_position = None

        elif self.current_page == PAGE_MEDIA:
            if position == "PREV":
                await self.layout_page()

            elif position == "NEXT":
                await self.clock_page()
            self.encoder_position = None

        elif self.current_page == PAGE_LAYOUT:
            if position == "PREV":
                await self.clock_page()

            elif position == "NEXT":
                self.media_page()

            self.encoder_position = None

        # acts as a memory to stay on the last visited page, file operation
        self.update_last_visited_page()


class MultiplexerManager:
    def __init__(self, S0, S1, S2, S3, SIG, MUX_SEL):
        self.select_pins = [
            digitalio.DigitalInOut(pin) for pin in [S0, S1, S2, S3]
        ]
        for pin in self.select_pins:
            pin.direction = digitalio.Direction.OUTPUT

        self.analog_input = analogio.AnalogIn(SIG)

        self.mux_sel = []
        for pin in MUX_SEL:
            mux_pin = digitalio.DigitalInOut(pin)
            mux_pin.direction = digitalio.Direction.OUTPUT
            self.mux_sel.append(mux_pin)

    def read_channel(self, channel, mux_sel):

        try:
            if mux_sel >= len(self.mux_sel):
                return 0

            # Enable selected multiplexer, disable others
            for i, mux in enumerate(self.mux_sel):
                mux.value = (i != mux_sel)

            # Set channel select pins
            for i, pin in enumerate(self.select_pins):
                pin.value = bool(channel & (1 << i))

            return self.analog_input.value

        except Exception as e:
            print(f"MUX error: {e}")
            return 0


class MacroPad:
    def __init__(self, multiplexer, configfile_manager, midi_manager):
        self.multiplexer = multiplexer
        self.configfile_manager = configfile_manager
        self.midi_manager = midi_manager
        self.kbd = Keyboard(usb_hid.devices)
        self.consumer = ConsumerControl(usb_hid.devices)
        self.kbd_layout = None
        self.rotary_layout = None

        # Constants
        self.BUTTON_COUNT = 16
        self.POT_COUNT = 8
        self.ENC_BTN_COUNT = 4
        self.BTN_THRESHOLD_LOW = 5000
        self.BTN_THRESHOLD_HIGH = 50000
        self.midi_enc_values = [64] * self.ENC_BTN_COUNT

        last_layout = self.configfile_manager.get("last_layout")
        layout_names = self.configfile_manager.keyboard_layouts_names()
        layout_names.append(MIDI_CONTROLLER_NAME)
        index = layout_names.index(last_layout)
        
        self.current_layout = last_layout
        print("CURRENT LAYOUT: ", self.current_layout)
        
        if self.current_layout != MIDI_CONTROLLER_NAME:

            current_kbd_layout, current_rotary_layout = (self.configfile_manager.
                                   keyboard_layout_values(index, last_layout))
    
            self.update_keyboard_layout(current_kbd_layout)
            self.update_rotary_layout(current_rotary_layout)

        # Initialize states
        self.pot_values = [0] * self.POT_COUNT
        self.button_states = [{"value": 0, "pressed": False} for _ in range(self.BUTTON_COUNT)]
        self.encoder_button_states = [{"value": 0, "pressed": False} for _ in range(self.ENC_BTN_COUNT)]

    async def update_values(self):
        while True:
            try:
                await self._update_buttons()
                await self._update_pots()
                await self._update_encoder_buttons()

                if ConfigFileManager.print_pot_values:
                    pot_values_str = "|".join(
                        str(int(interp(val, [0, 63535], [0, 4095])[0]))
                        for val in self.pot_values
                    )
                    # print(pot_values_str)
                    usb_cdc.data.write(f"{pot_values_str}\n".encode())

                await asyncio.sleep(0.01)
            except Exception as e:
                print(f"Update error: {e}")
                await asyncio.sleep(0.01)

    async def _update_buttons(self):
        for i in range(self.BUTTON_COUNT):
            value = self.multiplexer.read_channel(i, 0)
            self._process_button(i, value)
            await asyncio.sleep(0.001)

    async def _update_pots(self):
        for i in range(self.POT_COUNT):
            try:
                readings = [self.multiplexer.read_channel(i, 1) for _ in range(10)]
                self.pot_values[i] = sum(readings) // len(readings)  # Avoid division by zero

                if self.current_layout == MIDI_CONTROLLER_NAME:
                    self._process_pots(i)

                await asyncio.sleep(0.001)
            except Exception as e:
                print(f"Potentiometer read error: {e}")

    async def _update_encoder_buttons(self):
        for i in range(self.ENC_BTN_COUNT):
            value = self.multiplexer.read_channel(i + self.POT_COUNT, 1)
            await asyncio.sleep(0.001)
            self._process_encoder_button(i, value)

    def _process_pots(self, index):
        value = self.pot_values[index]
        value = int(interp(value, [0, 63535], [0, 127])[0])
        self.midi_manager.send_pots_value(index, value)

    def _process_button(self, index, value):
        state = self.button_states[index]

        if value < self.BTN_THRESHOLD_LOW and not state["pressed"]:
            print(f"Button {index} pressed")

            if self.current_layout != MIDI_CONTROLLER_NAME:
                for btns in self.kbd_layout[index]:
                    if btns is not None:
                        if btns in KC.__dict__.values():
                            self.kbd.press(btns)
                        elif btns in CC.__dict__.values():
                            self.consumer.press(btns)

            else:
                self.midi_manager.send_btn_value(self.BUTTON_COUNT + index, 127)

            state["pressed"] = True

        elif value > self.BTN_THRESHOLD_HIGH and state["pressed"]:
            print(f"Button {index} released")

            if self.current_layout != MIDI_CONTROLLER_NAME:
                for btns in self.kbd_layout[index]:
                    if btns is not None:
                        if btns in KC.__dict__.values():
                            self.kbd.release(btns)
                        elif btns in CC.__dict__.values():
                            self.consumer.release()

            else:
                self.midi_manager.send_btn_value(self.BUTTON_COUNT + index, 127)

            state["pressed"] = False

    def _process_encoder_button(self, index, value):
        state = self.encoder_button_states[index]

        if value < self.BTN_THRESHOLD_LOW and not state["pressed"]:
            print(f"Encoder button {index} pressed")

            if self.current_layout != MIDI_CONTROLLER_NAME:
                for btns in self.rotary_layout[3 * index + 1]:  # AP formula
                    if btns is not None:
                        if btns in KC.__dict__.values():
                            self.kbd.press(btns)
                        elif btns in CC.__dict__.values():
                            self.consumer.press(btns)

            else:
                self.midi_manager.send_btn_value(self.BUTTON_COUNT + index, 127)

            state["pressed"] = True

        elif value > self.BTN_THRESHOLD_HIGH and state["pressed"]:
            print(f"Encoder button {index} released")

            if self.current_layout != MIDI_CONTROLLER_NAME:
                for btns in self.rotary_layout[3 * index + 1]:  # AP formula
                    if btns is not None:
                        if btns in KC.__dict__.values():
                            self.kbd.release(btns)
                        elif btns in CC.__dict__.values():
                            self.consumer.release()

            else:
                self.midi_manager.send_btn_value(self.BUTTON_COUNT + index, 0)

            state["pressed"] = False

    def process_enc_direction(self, index, direction):
        # function called in rotary enc manager

        if direction == -1:  # Left turn on the encoder
            if self.current_layout != MIDI_CONTROLLER_NAME:
                keys_to_press = [vals for vals in self.rotary_layout[3 * index] if vals is not None]

                if keys_to_press and keys_to_press[0] is not None:
                    if keys_to_press[0] in KC.__dict__.values():
                        for key in keys_to_press:
                            self.kbd.send(key)

                    elif keys_to_press[0] in CC.__dict__.values():
                        for key in keys_to_press:
                            self.consumer.send(key)

            else:
                self.midi_enc_values[index] = max(0, self.midi_enc_values[index] - 1)
                self.midi_manager.send_enc_value(index, self.midi_enc_values[index])

        if direction == 1:  # Right turn on the encoder
            if self.current_layout != MIDI_CONTROLLER_NAME:
                keys_to_press = [vals for vals in self.rotary_layout[3 * index + 2] if vals is not None]

                if keys_to_press and keys_to_press[0] is not None:
                    if keys_to_press[0] in KC.__dict__.values():
                        for key in keys_to_press:
                            self.kbd.send(key)

                    elif keys_to_press[0] in CC.__dict__.values():
                        for key in keys_to_press:
                            self.consumer.send(key)

            else:
                self.midi_enc_values[index] = min(127, self.midi_enc_values[index] + 1)
                self.midi_manager.send_enc_value(index, self.midi_enc_values[index])

    def update_keyboard_layout(self, layout):
        self.kbd_layout = {
            i: [get_correct_keycode(key) for key in layout[i] if get_correct_keycode(key) is not None]
            for i in range(self.BUTTON_COUNT)
        }
        print("keyboard layout updated")
        # print(self.kbd_layout)

    def update_rotary_layout(self, layout):
        self.rotary_layout = {
            i: [get_correct_keycode(key) for key in layout[i] if get_correct_keycode(key) is not None]
            for i in range(self.ENC_BTN_COUNT*3)
        }
        print("rotary layout updated")


class MidiManager:

    def __init__(self):
        self.midi = adafruit_midi.MIDI(midi_out=usb_midi.ports[1], out_channel=0)
        self.button_ccs = range(20, 40)
        self.pot_ccs = range(10, 18)
        self.encoder_ccs = range(1,5)

    def send_btn_value(self, btn_index, value):
        self.midi.send(ControlChange(self.button_ccs[btn_index], value))

    def send_pots_value(self, pot_index, value):
        self.midi.send(ControlChange(self.pot_ccs[pot_index], value))

    def send_enc_value(self, enc_index, value):
        self.midi.send(ControlChange(self.encoder_ccs[enc_index], value))



class SerialManager:
    def __init__(self, display_manager):
        self.display_manager = display_manager
        self.rtc_manager = display_manager.rtc_manager

    async def handle_serial(self):
        while True:
            try:
                if usb_cdc.data.in_waiting > 0:
                    data = usb_cdc.data.readline().decode().strip()
                    await self._process_serial_data(data)
            except Exception as e:
                print(f"Serial error: {e}")
            await asyncio.sleep(0)

    async def _process_serial_data(self, data):
        if data.startswith("PING"):
            usb_cdc.data.write(b"ALIVE\n")

        elif data.startswith("TITLE"):
            title_data = data.split('|')
            self.display_manager.main_title = title_data[1]
            self.display_manager.sub_title = title_data[3]
            self.display_manager.is_media_title_changed = True

        elif data.startswith("CLOCK"):
            data = data.split('|')
            hour = data[1]
            minute = data[2]
            sec = data[3]
            date = data[4]
            month = data[5]
            year = data[6]
            week_day = data[7]

            print("setting time triggered")
            self.rtc_manager.set_time(hour, minute, date, month, year,sec, week_day)


class RotaryManager:
    def __init__(self, display_manager,macropad_manager, ctrl_pins, encoder_pins):
        self.display_manager = display_manager
        self.macropad_manager = macropad_manager
        self.ctrl_encoder = self._setup_control_encoder(*ctrl_pins)
        self.encoders = self._setup_encoders(encoder_pins)
        self.previous_positions = [0] * (len(encoder_pins) // 2 + 1)

    def _setup_control_encoder(self, dt, clk, btn):
        btn_pin = digitalio.DigitalInOut(btn)
        btn_pin.direction = digitalio.Direction.INPUT
        btn_pin.pull = digitalio.Pull.UP
        button = Debouncer(btn_pin)

        return {
            'encoder': rotaryio.IncrementalEncoder(dt, clk, divisor=2),
            'button': button
        }

    def _setup_encoders(self, pins):
        encoders = []
        for i in range(0, len(pins), 2):
            encoder = rotaryio.IncrementalEncoder(
                pins[i + 1], pins[i], divisor=2
            )
            encoders.append(encoder)
        return encoders

    async def process_encoders(self):
        while True:
            try:
                await self._process_control_encoder()
                await self._process_subsidiary_encoders()
                await asyncio.sleep(0.01)
            except Exception as e:
                print(f"Encoder error: {e}")
                await asyncio.sleep(1)

    async def _process_control_encoder(self):
        position = self.ctrl_encoder['encoder'].position
        if position != self.previous_positions[0]:
            self.display_manager.encoder_position = (
                "NEXT" if position > self.previous_positions[0] else "PREV"
            )
            self.ctrl_encoder['encoder'].position = 0
            self.previous_positions[0] = 0

        self.ctrl_encoder['button'].update()

        if self.ctrl_encoder['button'].fell:
            self.display_manager.encoder_position = "ONCLICK"

    async def _process_subsidiary_encoders(self):
        for i, encoder in enumerate(self.encoders, 1):
            position = encoder.position

            if position != self.previous_positions[i]:

                if position > self.previous_positions[i]:
                    self.macropad_manager.process_enc_direction(i-1, 1)

                else:
                    self.macropad_manager.process_enc_direction(i-1, -1)

                self.previous_positions[i] = 0
                encoder.position = 0

        await asyncio.sleep(0.001)



class RTCManager:
    def __init__(self, sda, scl):
        self.i2c = busio.I2C(scl, sda)
        self.rtc = adafruit_ds1307.DS1307(self.i2c)
        self.days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

    def set_time(self, hour, minute, date, month, year, sec=0, week_day=-1):
        """
        Set the RTC time with validation
        If week_day is -1, it will be calculated based on the date
        """
        # Ensure week_day is correctly set
        if week_day == -1:
            # Calculate day of week if not provided
            week_day = self._get_day_of_week(date, month, year)

        self.rtc.datetime = time.struct_time((int(year), int(month), int(date),
                                              int(hour), int(minute), int(sec),
                                              int(week_day), -1, -1))

    def current_time(self):
        """Get current time from RTC"""
        hour = self.rtc.datetime.tm_hour
        minute = self.rtc.datetime.tm_min
        sec = self.rtc.datetime.tm_sec
        date = self.rtc.datetime.tm_mday
        month = self.rtc.datetime.tm_mon
        year = self.rtc.datetime.tm_year
        day = self.days[self.rtc.datetime.tm_wday]

        return hour, minute, date, month, year, day

    def _get_day_of_week(self, day, month, year):
        """Calculate day of week using Zeller's Congruence algorithm"""
        if month < 3:
            month += 12
            year -= 1

        k = year % 100
        j = year // 100

        day_of_week = (day + 13 * (month + 1) // 5 + k + k // 4 + j // 4 - 2 * j) % 7

        # Convert from Zeller's result (0=Saturday) to standard weekday (0=Monday)
        day_of_week = (day_of_week + 5) % 7

        return day_of_week

class ConfigFileManager:

    def __init__(self):
        self.config_file_pth = "/config.json"
        self.keyboard_file_pth = "/keyboard_layouts.json"

        self.config_data = self._load_json(self.config_file_pth)
        self.keyboard_data = self._load_json(self.keyboard_file_pth)

        # self.keyboard_layout_values(0, "DEFAULT")

        # print("File loaded successfully")

    def _load_json(self, file_pth):
        """Load JSON data from file into memory."""
        try:
            with open(file_pth, "r") as file:
                return json.load(file)
        except (OSError, ValueError):  # File not found or JSON error
            return {}

    def get(self, key, default=None):
        """Get a value from the JSON data."""
        return self.config_data.get(key, default)

    def set(self, key, value):
        """Set a value in the JSON data (memory only)."""
        self.config_data[key] = value

    def save(self):
        """Write the JSON data back to the file safely."""
        json_string = json.dumps(self.config_data)  # Convert dict to JSON string

        # Overwrite file completely to avoid null characters
        with open(self.config_file_pth, "w") as file:
            file.write(json_string)  # Write the JSON string directly

    def print_pot_values(self):
        return self.config_data["print_pot_values"]

    def keyboard_layouts_names(self):
        return list(self.keyboard_data.keys())

    def keyboard_layout_values(self, layout_index, layout_name):
        # Access the correct dictionary directly
        layout_data = self.keyboard_data.get(layout_name, {})

        kbd_data = layout_data.get("buttons", [])
        rotary_data = layout_data.get("rotary", [])

        # Process keyboard buttons
        kbd_layout = []
        for value in kbd_data:
            if isinstance(value, str):  # Ensure it's a string before splitting
                kbd_layout.append(value.split())  # Split if multi-word (e.g., "CONTROL A")
            else:
                kbd_layout.append([value])  # Wrap single key in a list

        # Process rotary encoder buttons
        rotary_layout = []
        for value in rotary_data:
            if isinstance(value, str):  # Ensure it's a string before splitting
                rotary_layout.append(value.split())  # Split if multi-word (e.g., "CONTROL A")
            else:
                rotary_layout.append([value])  # Wrap single key in a list

        return kbd_layout, rotary_layout

async def main():
    try:
        # Initialize components
        time.sleep(3)
        configfile_manager = ConfigFileManager()
        # print("CONFIG MANAGER DONE")
        # kbd_layout = {i: getattr(KC, chr(ord("A") + i)) for i in range(12)}

        multiplexer = MultiplexerManager(
            S0=board.GP10, S1=board.GP11, S2=board.GP12, S3=board.GP13,
            SIG=board.GP28, MUX_SEL=[board.GP14, board.GP15]
        )
        # print("MULTIPLEXER MANAGER DONE")
        
        midi_manager = MidiManager()
        
        macropad = MacroPad(multiplexer=multiplexer, configfile_manager=configfile_manager,
                            midi_manager=midi_manager)
        print("MACROPAD MANAGER DONE")

        rtc_manager = RTCManager(sda=board.GP18, scl=board.GP19)
        # print("RTC MANAGER DONE")

        display_manager = DisplayManager(sda=board.GP16, scl=board.GP17,
                                         rtc_manager=rtc_manager,
                                         configfile_manager=configfile_manager,
                                         macropad_manager=macropad)
        # print("DISPLAY MANAGER DONE")

        serial_manager = SerialManager(display_manager)
        # print("SERIAL MANAGER DONE")

        rotary_manager = RotaryManager(
            display_manager=display_manager,
            macropad_manager=macropad,
            ctrl_pins=(board.GP0, board.GP1, board.GP20),
            encoder_pins=[
                board.GP2, board.GP3, board.GP4, board.GP5,
                board.GP6, board.GP7, board.GP8, board.GP9
            ]
        )
        # print("ROTARY MANAGER DONE")

        await display_manager.display_last_page()


        # Create and run tasks
        tasks = [
            asyncio.create_task(macropad.update_values()),
            asyncio.create_task(serial_manager.handle_serial()),
            asyncio.create_task(display_manager.update_display()),
            asyncio.create_task(display_manager.check_curr_time()),
            asyncio.create_task(rotary_manager.process_encoders()),
        ]

        await asyncio.gather(*tasks)

    except Exception as e:
        print(f"Main loop error: {e}")
        gc.collect()


if __name__ == "__main__":
    asyncio.run(main())
