import threading

# made this running on a separate thread
decibels = [-65.25, -59.0, -54.0, -49.0, -46.0, -43.0, -40.0, -38.0, -37.0, -35.0, -33.0, -32.0,
            -31.0, -30.0, -29.0, -28.0, -27.0, -26.0, -25.0, -24.7, -24.0, -23.0, -22.0, -21.8,
            -21.0, -20.7, -20.0, -19.5, -18.9, -18.5, -17.9, -17.4, -17.0, -16.5, -16.0, -15.5,
            -15.1, -14.8, -14.4, -13.95, -13.6, -13.3, -12.9, -12.6, -12.2, -11.9, -11.6, -11.3,
            -10.9, -10.6, -10.3, -10.0, -9.75, -9.5, -9.2, -8.95, -8.6, -8.5, -8.2, -8.0, -7.7,
            -7.5, -7.2, -7.0, -6.7, -6.5, -6.3, -6.0, -5.8, -5.6, -5.4, -5.2, -5.0, -4.8, -4.6,
            -4.4, -4.2, -4.0, -3.8, -3.6, -3.4, -3.2, -3.0, -2.8, -2.6, -2.5, -2.3, -2.1, -2.0,
            -1.8, -1.6, -1.4, -1.3, -1.1, -1.0, -0.8, -0.6, -0.5, -0.3, -0.15, 0.0]


class VolumeControl:
    def __init__(self):
        self.volume = None
        self.initialized = threading.Event()
        self.audio_utilities = None

        # Start the initialization thread
        threading.Thread(target=self._initialisation_thread, daemon=True).start()
        self.initialized.wait()  # Wait until the thread signals completion

    def _initialisation_thread(self):
        # Import inside the thread to avoid global conflicts
        from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
        from comtypes import CLSCTX_ALL

        try:
            self.audio_utilities = AudioUtilities
            self.devices = AudioUtilities.GetSpeakers()
            self.interface = self.devices.Activate(
                IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
            self.volume = self.interface.QueryInterface(IAudioEndpointVolume)
        finally:
            self.initialized.set()  # Signal that initialization is complete

    def set_volume(self, name: str, value: int):
        if name == "MASTER_VOLUME":
            if not self.volume:
                print("Volume interface not initialized.")
                return

            self.volume.SetMasterVolumeLevel(decibels[value], None)


        else:

            from pycaw.pycaw import AudioUtilities

            sessions = AudioUtilities.GetAllSessions()

            for session in sessions:

                # noinspection PyBroadException
                try:

                    if session.Process and session.Process.name() == name:
                        interface = session.SimpleAudioVolume

                        # Uncomment and modify the volume setting

                        interface.SetMasterVolume(value / 100.0, None)

                        # print(f"Set volume for {name} to {value}")

                        # break  # Exit after setting volume for the first matching process

                except:
                    pass
