from PIL import Image
import io


def jpeg_to_cpp_array(image_path, array_name="image_data"):
    """Convert a JPEG image into a C++ byte array."""
    # Open the image and ensure it's in JPEG format
    with Image.open(image_path) as img:
        if img.format != 'JPEG':
            raise ValueError("The provided image is not in JPEG format.")

        # Save the JPEG data into a bytes buffer
        buffer = io.BytesIO()
        img.save(buffer, format="JPEG")
        jpeg_data = buffer.getvalue()

    # Start building the C++ code
    cpp_code = []
    cpp_code.append(f"const uint8_t {array_name}[] PROGMEM = {{")

    # Convert the JPEG bytes into a C++ byte array format (16 bytes per line)
    for i in range(0, len(jpeg_data), 16):
        line = jpeg_data[i:i + 16]
        hex_values = [f"0x{byte:02X}" for byte in line]
        cpp_code.append("    " + ", ".join(hex_values) + ",")

    cpp_code[-1] = cpp_code[-1].rstrip(",")  # Remove trailing comma from the last line
    cpp_code.append("};")

    # Add a comment with the total data size
    cpp_code.insert(0, f"// Total size: {len(jpeg_data)} bytes")

    return "\n".join(cpp_code)


# Example usage
if __name__ == "__main__":
    # Path to the JPEG image
    image_path = 'no media.jpg'

    # Convert the image to a C++ byte array
    cpp_data = jpeg_to_cpp_array(image_path, array_name="brightness_menu")

    # Save the output to a header file
    with open('image_data.h', 'w') as f:
        f.write(cpp_data)
        print("Generated image_data.h")

    # Print preview of the output
    print("\nPreview:")
    print("\n".join(cpp_data.split("\n")[:10]))
