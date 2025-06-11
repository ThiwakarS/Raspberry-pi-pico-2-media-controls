import pyserial
import media_session
import volume_potentiometer
import time
from numpy import interp
import yaml


def process_received_data(data, volume_obj, no_of_sliders, slider_functions):
    if data is None or len(data) != no_of_sliders:
        return

    for i in range(no_of_sliders):
        try:
            # print(data)
            vol_lvl = map_potentiometer_value(data[i])
            volume_obj.set_volume(name=slider_functions[i], value=vol_lvl)
            # time.sleep(0.5)
        except Exception as e:
            print(f"Cannot set volume error: {e}")


def map_potentiometer_value(value):
    return int(interp(int(value), [5, 4090], [0, 100]))


def main():
    try:
        with open('config.yaml', 'r') as file:
            file_service = yaml.safe_load(file)
            slider_functions = file_service['slider_functions']

            no_of_sliders = len(slider_functions)

    except Exception as e:
        print(f"Error reading config.yaml: {e}")
        return

    serial_obj = pyserial.SerialConnection(no_of_sliders)
    time.sleep(1)
    volume_obj = volume_potentiometer.VolumeControl()
    time.sleep(1)

    # Pass serial_obj to Media class for direct image sending
    media_obj = media_session.Media(serial_obj=serial_obj)
    time.sleep(1)

    print("Everything Initialised")

    try:
        while True:
            process_received_data(data=serial_obj.data, volume_obj=volume_obj,
                                  no_of_sliders=no_of_sliders, slider_functions=slider_functions)

            time.sleep(0.01)

    except Exception as e:
        print(f"Exception occurred, stopping: {e}")

    finally:
        media_obj.stop()
        serial_obj.stop()


if __name__ == "__main__":
    main()
