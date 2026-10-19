# casio-exam-mode-unlocker

**Language:** English | [Français](README.fr.md)

Standalone Linux utility to exit Exam Mode on first-generation Casio graphing calculators over USB. It bypasses the blocked `CESG64.sys` driver on modern Windows systems and provides a native alternative to the missing official Linux software.

## Supported hardware

Calculators using the Casio USB interface (`07cf:6101`):
- Graph 35+E (first generation)
- Graph 75+E
- fx-9750GII
- fx-9860GII

### Recent mass storage models

Recent calculators do not require this script:
- Graph 35+E II
- Graph 90+E
- fx-CG50

These models expose standard USB Mass Storage. To exit Exam Mode:
1. Connect the calculator to a computer with a USB cable.
2. Select USB Flash mode (press F1 on the calculator).
3. Open the mounted drive in your file manager and create, copy, or delete any small file.
4. Safely eject the drive and disconnect the cable. The calculator exits Exam Mode automatically.

## Requirements

- Python 3 (standard library only: `ctypes`, `sys`). No `pip` packages required.
- `libusb-1.0` (installed via `libusb-1.0-0` on Debian, Ubuntu, and Linux Mint).

## Usage

Connect the calculator to the computer with a USB cable, turn it on, and run:

```bash
sudo python3 unlock_casio.py
```

Root privileges are required because Linux restricts direct write access to raw USB character devices (`/dev/bus/usb/...`).

### Running without sudo

To allow regular users in the `plugdev` group to access the calculator without `sudo`, configure a udev rule:

```bash
echo 'SUBSYSTEM=="usb", ATTR{idVendor}=="07cf", ATTR{idProduct}=="6101", MODE="0660", GROUP="plugdev"' | sudo tee /etc/udev/rules.d/99-casio.rules
sudo udevadm control --reload-rules
sudo udevadm trigger
```

Disconnect and reconnect the USB cable, then run:

```bash
python3 unlock_casio.py
```

## Troubleshooting

- **`Error: calculator not found or permission denied. Run with sudo.`**
  The script cannot open USB device `07cf:6101`. Ensure the calculator is powered on and firmly connected. If the cable is connected, ensure you are running the script with `sudo` or have configured the udev rule above.
- **`Error: failed to load libusb: ...`**
  The system `libusb-1.0` shared library is missing. Install it on Debian, Ubuntu, or Linux Mint using `sudo apt install libusb-1.0-0`.
- **`Error: unexpected response to ENQ` or `Error: unexpected response to CAN`**
  The calculator returned an unexpected handshake payload. Verify that your calculator model uses the `07cf:6101` interface and is currently locked in Exam Mode.

## Platform support and limitations

- **Linux:** Fully tested and functional natively. Does not require custom kernel modules or third-party drivers.
- **Windows:** Untested with this script. On Windows 10 and 11, Core Isolation (Memory Integrity) blocks Casio's official driver (`CESG64.sys`) with the error "A driver cannot load on this device: CESG64.sys". Running this Python script on Windows would require replacing the blocked driver with WinUSB using Zadig and placing `libusb-1.0.dll` in the script directory.
- **macOS:** Untested with this script. Running it on macOS requires installing `libusb` (for example via `brew install libusb`).

## Reverse engineering

The official Windows utility (`Exam_Mode_Unlocker_Ver.1.00.exe`) is an InstallShield wrapper around the blocked `CESG64.sys` driver. To determine the communication protocol, we examined the official macOS bundle (`Exam Mode Unlocker.app`).

1. Extracted the Mach-O x86_64 executable located at `Contents/MacOS/Exam Mode Unlocker`.
2. Inspected the symbol table (`LC_SYMTAB`) and identified functions in `USBPipes.o`:
   - `USBPipes::PerformUnlock`
   - `USBPipes::FindPipes`
   - `request_unlock_command`
3. Disassembled `PerformUnlock` with `objdump`, revealing the underlying USB transfer sequence:
   - Claim interface 0 on device `07cf:6101`.
   - Clear halts on endpoints `0x01` (Bulk OUT) and `0x82` (Bulk IN).
   - Write 6 bytes to endpoint `0x01`: `\x0500070` (ENQ).
   - Read 6 bytes from endpoint `0x82`: expect `\x0600070` (ACK).
   - Write 6 bytes to endpoint `0x01`: `\x1800070` (CAN / unlock).
   - Read 6 bytes from endpoint `0x82`: expect `\x0600070` (ACK).

The calculator clears Exam Mode immediately after receiving the second ACK packet.
