# Multi-Functional MacroPad with OLED Display

A versatile, customizable macropad built with Raspberry Pi Pico that features programmable buttons, rotary encoders, potentiometers, and an OLED display for media information and system controls.

## ✨ Features

### 🎛️ Hardware Components
- **16 Programmable Buttons** - Fully customizable macros and shortcuts
- **4 Rotary Encoders** - With clickable buttons for additional functionality
- **8 Potentiometers** - Analog controls for volume, brightness, or custom parameters
- **128x64 OLED Display** - Real-time information and navigation interface
- **Real-Time Clock (RTC)** - Accurate timekeeping with battery backup
- **USB-C Connectivity** - Power and data communication

### 💻 Software Features
- **Custom Layout System** - Define your own button mappings and encoder functions
- **Media Display Integration** - Shows currently playing media information
- **Multiple Operating Modes**:
  - **Keyboard Mode** - Custom key combinations and shortcuts
  - **MIDI Controller Mode** - Full MIDI CC control for music production
- **Real-Time Clock Display** - Time, date, and calendar with manual adjustment
- **Layout Switching** - Quick switching between different control schemes
- **Volume Control Integration** - Direct system volume control via potentiometers

### 🖥️ Display Pages
1. **Media Page** - Current playing song title and artist
2. **Clock Page** - Time, date, and day of week with settings
3. **Layout Page** - Switch between different control configurations

## 🛠️ Hardware Requirements

### Components List
- Raspberry Pi Pico (or compatible RP2040 board)
- 128x64 I2C OLED Display (SSD1306)
- DS1307 Real-Time Clock Module
- 2x CD74HC4067 16-channel analog multiplexers
- 16x Tactile push buttons
- 4x Rotary encoders with push buttons
- 8x 10kΩ Linear potentiometers
- Various resistors, capacitors, and connecting wires
- Custom PCB or breadboard for assembly

### Pin Configuration
```
Display (SSD1306):  SDA=GP16, SCL=GP17
RTC (DS1307):       SDA=GP18, SCL=GP19
Control Encoder:    DT=GP0, CLK=GP1, BTN=GP20
Subsidiary Encoders: GP2-GP9 (4 encoders, 2 pins each)
Multiplexer Control: S0=GP10, S1=GP11, S2=GP12, S3=GP13
Multiplexer Select:  GP14, GP15
Analog Input:        GP28
```

## 🚀 Installation & Setup

### 1. Hardware Assembly
1. Connect all components according to the pin configuration
2. Ensure proper power distribution (3.3V and GND)
3. Test all connections before powering on

### 2. Firmware Installation
1. Install CircuitPython on your Raspberry Pi Pico
2. Copy the following files to the CIRCUITPY drive:
   ```
   /code.py (renamed from pico_test.py)
   /config.json
   /keyboard_layouts.json
   ```

### 3. Required CircuitPython Libraries
Install these libraries in the `/lib` folder:
```
adafruit_displayio_ssd1306
adafruit_display_text
adafruit_ds1307
adafruit_debouncer
adafruit_midi
adafruit_hid
```

### 4. Python Host Software
1. Install Python dependencies:
   ```bash
   pip install pyserial pycaw numpy pyyaml
   ```
2. Create `config.yaml` file:
   ```yaml
   slider_functions:
     - "master"      # Volume control names
     - "chrome"
     - "discord"
     - "spotify"
     - "system"
     - "microphone"
     - "game"
     - "music"
   ```

## ⚙️ Configuration

### Layout Configuration
Edit `keyboard_layouts.json` to define custom layouts:

```json
{
  "DEFAULT": {
    "buttons": [
      "A", "B", "C", "D",
      "CONTROL C", "CONTROL V", "CONTROL Z", "CONTROL Y",
      "F1", "F2", "F3", "F4",
      "MEDIA_PLAY_PAUSE", "MEDIA_NEXT_TRACK", "MEDIA_PREVIOUS_TRACK", "MUTE"
    ],
    "rotary": [
      "VOLUME_DECREMENT", "MEDIA_PLAY_PAUSE", "VOLUME_INCREMENT",
      "LEFT_ARROW", "ENTER", "RIGHT_ARROW",
      "PAGE_UP", "SPACE", "PAGE_DOWN",
      "CONTROL MINUS", "CONTROL ZERO", "CONTROL EQUALS"
    ]
  },
  "GAMING": {
    "buttons": ["W", "A", "S", "D", ...],
    "rotary": [...]
  }
}
```

### System Settings
Modify `config.json` for system preferences:
```json
{
  "last_page": "MEDIA",
  "last_layout": "DEFAULT",
  "print_pot_values": true
}
```

## 🎮 Usage Guide

### Navigation
- **Control Encoder**: 
  - Rotate: Switch between pages (Media → Clock → Layouts)
  - Click: Enter settings mode for current page

### Media Page
- Displays currently playing media title and artist
- Updates automatically when media changes
- Shows "No Media" when nothing is playing

### Clock Page
- **Normal View**: Shows current time, date, and day
- **Settings Mode** (click control encoder):
  - Click to cycle through: Hour → Minute → Year → Month → Day
  - Rotate to adjust selected value
  - Click past Day to exit settings

### Layout Page  
- **Normal View**: Shows current active layout
- **Settings Mode** (click control encoder):
  - Rotate to browse available layouts
  - Click to select and activate layout

### Button Functions
- **Keyboard Mode**: Sends configured key combinations
- **MIDI Mode**: Sends MIDI Control Change messages
- Supports complex combinations (e.g., "CONTROL SHIFT A")

### Rotary Encoders
- Each encoder has three functions:
  - Counter-clockwise rotation
  - Button press
  - Clockwise rotation
- **MIDI Mode**: Sends incremental CC values (0-127)

### Potentiometers
- **Keyboard Mode**: Can trigger volume controls via host software
- **MIDI Mode**: Send continuous MIDI CC values
- Values smoothed with 10-sample averaging

## 🔧 Advanced Features

### Volume Control Integration
The host software (`main.py`) provides system-wide volume control:
- Maps potentiometer values to volume levels (0-100%)
- Supports per-application volume control
- Real-time updates without audio interruption

### MIDI Controller Mode
- Full MIDI implementation with customizable CC numbers
- Button CCs: 20-39
- Potentiometer CCs: 10-17  
- Encoder CCs: 1-4
- Compatible with DAWs like Ableton Live, FL Studio, etc.

### Layout Memory
- Automatically remembers last used page and layout
- Persistent storage survives power cycles
- Quick switching between different workflows

## 🐛 Troubleshooting

### Common Issues

**Display not working:**
- Check I2C connections (SDA/SCL)
- Verify display address (0x3C)
- Ensure 3.3V power supply

**Buttons not responding:**
- Check multiplexer connections
- Verify threshold values in code
- Test with multimeter for proper voltage levels

**Serial communication issues:**
- Ensure correct COM port detection
- Check baud rate (115200)
- Verify USB cable supports data transfer

**RTC not keeping time:**
- Replace CR2032 battery
- Check I2C connections to DS1307
- Verify crystal oscillator (32.768kHz)

### Debug Mode
Enable debug output by setting `print_pot_values: true` in config.json

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

### Development Guidelines
- Follow existing code structure and naming conventions
- Test all hardware interfaces before submitting
- Update documentation for new features
- Maintain backward compatibility when possible

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- CircuitPython community for excellent libraries
- Adafruit for comprehensive hardware support
- Contributors and testers who helped refine the project

## 📞 Support

For questions, issues, or feature requests:
- Open an issue on GitHub
- Check the troubleshooting section above
- Review existing discussions and solutions

---

**Happy Macro-ing! 🎛️✨**
