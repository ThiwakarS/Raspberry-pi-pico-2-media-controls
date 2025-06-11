import time
import serial
import serial.tools.list_ports_windows
import logging
import threading
from datetime import datetime

class SerialConnection:
    def __init__(self, no_of_sliders):

        # Configure logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)

        # Serial connection parameters
        self.COM_PORT = None
        self.BAUD_RATE = 115200
        self.ser = None
        self.data = []
        self.connected = False
        self.no_of_sliders = no_of_sliders
        self.serial_lock = False

        # Synchronization events and queues
        self.connection_event = threading.Event()
        self.stop_event = threading.Event()

        # Existing threads (connection and read threads)
        self.serial_connection_thread = threading.Thread(
            target=self._start_and_check_conn_thread,
            daemon=True
        )
        self.serial_read_thread = threading.Thread(
            target=self._read_data_thread,
            daemon=True
        )

        # Start all threads
        self.serial_connection_thread.start()
        self.serial_read_thread.start()

    def _start_and_check_conn_thread(self):
        """Continuously manage serial connection."""
        while not self.stop_event.is_set():
            try:
                if not self.connected:
                    self._start_connection()
                else:
                    self._check_connection()

            except Exception as e:
                self.logger.error(f"Connection management error: {e}")
                self.connected = False

            time.sleep(5)

    # noinspection PyUnresolvedReferences
    def _start_connection(self):
        """Find and establish connection with ESP32."""
        while self.serial_lock:
            print("start connection returns none, serial lock true")
            time.sleep(1)

        if self.ser and self.ser.is_open:
            self.ser.close()
            time.sleep(2)

        self.serial_lock = True

        ports = self._find_pico_port()
        if not ports:
            self.logger.warning("No PICO ports found")
            return

        for port in ports:
            try:
                self.ser = serial.Serial(
                    port=port,
                    baudrate=self.BAUD_RATE,
                    bytesize=serial.EIGHTBITS,
                    parity=serial.PARITY_NONE,
                    stopbits=serial.STOPBITS_ONE,
                    timeout=1
                )
                # self.ser.setRTS(False)
                # self.ser.setDTR(False)
                self.COM_PORT = port
                self.connected = True
                self.connection_event.set()
                self.logger.info(f"Connected to PICO on {self.COM_PORT}")

                self.serial_lock = False

                time.sleep(1)

                self.send_time_to_pico()

                return
            except (serial.SerialException, OSError) as e:
                self.logger.error(f"Failed to connect to {port}: {e}")
                self.serial_lock = False

    def _check_connection(self):
        """Verify active serial connection."""
        if not self.ser or not self.ser.is_open:
            self.connected = False
            return

        while self.serial_lock:
            print("Serial lock not acquired, check connection")
            time.sleep(1)

        try:
            # Send a ping and check response
            self.serial_lock = True

            self.ser.reset_input_buffer()
            self.ser.write('PING\n'.encode())

            self.serial_lock = False

        except Exception as e:
            self.logger.error(f"Connection verification failed: {e}")
            self.connected = False
            self.serial_lock = False


    def _read_data_thread(self):
        """Read serial data continuously."""
        while not self.stop_event.is_set():
            try:
                # Wait for connection to be established
                self.connection_event.wait(timeout=5)

                if self.connected and self.ser and self.ser.is_open:
                    data = self._read_serial_data()
                    if data and data[0] == "ALIVE":
                        self.connected = True
                    elif data and len(data) == self.no_of_sliders:
                        self.data = data
                        ### PROCESSING RECEIVED DATA FOR BUTTONS AND SWITCHES
                        ### IS DONE IN MAIN.PY FILE

                    else:
                        self.data = []

                time.sleep(0.01)

            except Exception as e:
                self.logger.error(f"Data reading error: {e}")
                self.connected = False
                time.sleep(1)

    def _read_serial_data(self):
        """Read and parse serial data."""
        try:
            if self.ser.in_waiting:
                raw_data = self.ser.readline()
                data = raw_data.decode('utf-8', errors='ignore').strip()
                data = data.split('|')
                # print(data)
                if data:
                    return data

                return None

        except Exception as e:
            self.logger.error(f"Serial data reading error: {e}")
        return None

    def stop(self):
        """Stop all threads and close connection."""
        self.stop_event.set()
        self.connection_event.set()
        self.serial_lock = False
        # self.media_obj.stop()
        # self.keyboard_handler.key_listener.stop()
        if self.ser and self.ser.is_open:
            self.ser.close()
            time.sleep(1)

    def send_title_to_pico(self, title="", sub_title=""):
        if not self.ser:
            return

        while self.serial_lock:
            print("Serial lock not acquired, send title to pico")
            time.sleep(1)

        try:
            self.serial_lock = True

            self.ser.write(f"TITLE|{title}|SUB|{sub_title}\n".encode())

            self.serial_lock = False

        except Exception as e:
            print(f"Error in sending title to pico: {e}")
            self.serial_lock = False

    def send_time_to_pico(self):

        try :
            while self.serial_lock:
                print("Serial lock not acquired, sending time to pico")
                time.sleep(1)

            self.serial_lock = True

            now = datetime.now()

            string = datetime.isoformat(now)

            date = string.split('T')

            time_ = date[1]
            date = date[0]

            year = date.split('-')
            date = year[2]
            month = year[1]
            year = year[0]

            sec = time_.split(':')
            hour = sec[0]
            minute = sec[1]
            sec = sec[2][:2]

            weekday = datetime.weekday(now)
            string = f"CLOCK|{hour}|{minute}|{sec}|{date}|{month}|{year}|{weekday}\n"
            print("sending time")
            self.ser.write(string.encode())

            self.serial_lock = False

        except Exception as e:
            print(f"Exception occurred while sending time to pico: {e}")
            self.serial_lock = False

    @staticmethod
    def _find_pico_port():
        """Find available ESP32 USB ports."""
        ports = serial.tools.list_ports_windows.comports()
        return [port.device for port in ports if "USB" in str(port.hwid)]