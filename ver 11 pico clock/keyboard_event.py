# from pynput import keyboard
#
# VALID_KEY_COMMANDS = {"ctrl": keyboard.Key.ctrl, "shift": keyboard.Key.shift,
#                       "alt": keyboard.Key.alt, "esc": keyboard.Key.esc,
#                       "enter": keyboard.Key.enter, "backspace": keyboard.Key.backspace,
#                       "print_screen": keyboard.Key.print_screen, "home": keyboard.Key.home,
#                       "page_up": keyboard.Key.page_up, "page_down": keyboard.Key.page_down,
#                       "tab": keyboard.Key.tab, "windows_key": keyboard.Key.cmd,
#                       "delete": keyboard.Key.delete, "play_pause": keyboard.Key.media_play_pause,
#                       "media_previous": keyboard.Key.media_previous, "media_next": keyboard.Key.media_next,
#                       "media_volume_mute": keyboard.Key.media_volume_mute}
#
# # VALID_CHARACTERS = "qwertyuiopasdfghjklzxcvbnmQWERTYUIOPASDFGHJKLZXCVBNM1234567890,./;'[]{}|=-+_)(*&^%$#@!~`\\"
#
# def on_press(key: keyboard.Key):
#     try:
#         if key == keyboard.Key.media_play_pause:
#             print("Play pause pressed")
#         elif key == keyboard.Key.media_next:
#             print("Skip next pressed")
#         elif key == keyboard.Key.media_previous:
#             print("Skip previous pressed")
#         elif key == keyboard.Key.media_volume_mute:
#             print("volume mute pressed")
#
#     except AttributeError:
#         print("Attribute error")
#     except Exception as e:
#         print("Key error: " + str(e))
#
#
# def press_and_release_key(key):
#     key_controller = keyboard.Controller()
#
#     for i in key:
#         if i in VALID_KEY_COMMANDS:
#             key_controller.press(VALID_KEY_COMMANDS[i])
#         else:
#             key_controller.press(i)
#
#     for i in key:
#         if i in VALID_KEY_COMMANDS:
#             key_controller.release(VALID_KEY_COMMANDS[i])
#         else:
#             key_controller.release(i)
#
#
# def validate_key(key):
#     keys = key.split()
#     print(keys)
#
#     try:
#         press_and_release_key(keys)
#
#     except Exception as e:
#         print(f"Error in shortcut: {e}")
#
#
#
# key_listener = keyboard.Listener(on_press=on_press)
# key_listener.start()  ### stops in case of exception on the main.py file
