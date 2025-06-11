import threading
import asyncio
from winrt.windows.media.control import \
    GlobalSystemMediaTransportControlsSessionManager as MediaManager
from winrt.windows.storage.streams import DataReader, Buffer, InputStreamOptions
from PIL import Image
from io import BytesIO

class Media:
    def __init__(self, serial_obj=None):
        # Initialize session management
        self.session_thread = None
        self.session_timer_interval = 0.5  # Check session every 0.5sec
        self.current_session_flag = False
        self.title = None
        self.artist = None
        self.current_media_thumbnail = None
        self.serial_obj = serial_obj  # Reference to SerialConnection

        # Event to handle stopping
        self.stop_event = threading.Event()

        # Async loop for managing media sessions
        self.session_loop = asyncio.new_event_loop()

        # Start session thread
        self.session_thread = threading.Thread(
            target=self._async_session_thread, daemon=True)
        self.session_thread.start()

    def stop(self):
        """Gracefully stop the media session."""
        self.stop_event.set()

        try:
            # Stop the asyncio loop
            # noinspection PyTypeChecker
            self.session_loop.call_soon_threadsafe(self.session_loop.stop)
        except Exception as e:
            print(f"Error stopping event loop: {e}")

        # Ensure threads stop properly
        self.session_thread.join(timeout=2)

    def _async_session_thread(self):
        """Thread to run the asyncio loop."""
        asyncio.set_event_loop(self.session_loop)
        try:
            self.session_loop.run_until_complete(self._async_session_runner())
        except Exception as e:
            print(f"Error in async session thread: {e}")
        finally:
            try:
                self.session_loop.close()
            except Exception as e:
                print(f"Error closing event loop: {e}")

    async def _async_session_runner(self):
        """Async runner to manage media sessions."""
        while not self.stop_event.is_set():
            try:
                await self._async_session_handler()
                await asyncio.sleep(self.session_timer_interval)
            except Exception as e:
                print(f"Error in async session handler: {e}")
                await asyncio.sleep(0.5)  # Add delay to avoid busy-waiting on errors

    # async def load_thumbnail(self, thumb_stream_ref):
    #     """Loads and displays the media thumbnail."""
    #     try:
    #         thumb_read_buffer = Buffer(5000000)  # Allocate buffer for thumbnail
    #         readable_stream = await thumb_stream_ref.open_read_async()  # Open thumbnail stream
    #
    #         # Read the stream data into the buffer
    #         await readable_stream.read_async(
    #             thumb_read_buffer,
    #             thumb_read_buffer.capacity,
    #             InputStreamOptions.READ_AHEAD
    #         )
    #
    #         # Convert buffer data into an image
    #         buffer_reader = DataReader.from_buffer(thumb_read_buffer)
    #         byte_buffer = buffer_reader.read_bytes(thumb_read_buffer.length)
    #         binary = BytesIO(bytearray(byte_buffer))
    #         img = Image.open(binary)
    #         img.convert("RGB")
    #         self.current_media_thumbnail = img  # Update the current thumbnail
    #         # img.save("thumbnail_test.jpg", format="JPEG")
    #
    #         # Clean up resources
    #         binary.close()
    #         readable_stream.close()
    #         return self.current_media_thumbnail
    #     except Exception as e:
    #         print(f"Failed to load thumbnail: {str(e)}")
    #         return None

    async def _async_session_handler(self):
        """Handle media session updates."""
        try:
            session_manager = await MediaManager.request_async()
            current_session = session_manager.get_current_session()

            if not current_session:
                if self.current_session_flag:
                    print("No current session available")
                    self.current_session_flag = False
                    self.title = None
                    self.artist = None
                    #self.serial_obj.send_image_to_pico(Image.open('no media.jpg'), no_media_flg=True)
                    self.serial_obj.send_title_to_pico(
                        "No Media",
                        "currently playing"
                    )
                return

            media_properties = await current_session.try_get_media_properties_async()

            # Check for updated media session properties
            if media_properties.title != self.title:
                self.title = media_properties.title
                self.artist = media_properties.artist
                self.current_session_flag = True

                print(f"Now Playing: Title: {self.title}, Artist: {self.artist}")

                # Send image to ESP32 if serial object is available
                if self.serial_obj:
                        # Direct send without using queue
                    self.serial_obj.send_title_to_pico(
                        self.title,
                        self.artist
                    )
                elif not media_properties.thumbnail:
                    print("No thumbnail available")

        except Exception as e:
            print(f"Error managing media session: {e}")
            self.current_session_flag = False
            self.title = None
            self.artist = None
