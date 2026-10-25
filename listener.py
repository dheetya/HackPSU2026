import serial
import time

ARDUINO_PORT = "COM3"  # Update if yours is different
BAUD_RATE = 9600

print(f"Attempting to connect to Arduino on {ARDUINO_PORT}...")

try:
    ser = serial.Serial(ARDUINO_PORT, BAUD_RATE, timeout=1)
    time.sleep(2)  # Give the connection a second to settle
    print("Successfully connected! Listening for button presses...")
except Exception as e:
    print(f"CONNECTION ERROR: {e}")
    exit()

while True:
    try:
        if ser.in_waiting > 0:
            command = ser.readline().decode("utf-8").strip()
            if command:
                print(f"Hardware Pressed: {command}")
                with open("command.txt", "w") as f:
                    f.write(command)
    except Exception as e:
        print(f"Read error: {e}")
        break