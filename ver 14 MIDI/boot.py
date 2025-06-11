import board
import digitalio
import storage
import usb_cdc

# Configure a switch on GP0 to determine read-only mode for storage
switch = digitalio.DigitalInOut(board.GP0)
switch.direction = digitalio.Direction.INPUT
switch.pull = digitalio.Pull.UP

# Enable both console and data channels for USB CDC
usb_cdc.enable(console=True, data=True)

# Mount the filesystem as read-only or read-write based on the switch state
storage.remount("/", readonly=switch.value)
