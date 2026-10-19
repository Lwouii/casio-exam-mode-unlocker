#!/usr/bin/env python3
"""Exits Exam Mode on Casio USB calculators using raw libusb bulk transfers."""

import ctypes
import ctypes.util
import sys

libname = ctypes.util.find_library("usb-1.0") or "libusb-1.0.so.0"
try:
    libusb = ctypes.CDLL(libname)
except OSError as err:
    print(f"Error: failed to load libusb: {err}", file=sys.stderr)
    sys.exit(1)

libusb.libusb_init.argtypes = [ctypes.POINTER(ctypes.c_void_p)]
libusb.libusb_init.restype = ctypes.c_int

libusb.libusb_exit.argtypes = [ctypes.c_void_p]
libusb.libusb_exit.restype = None

libusb.libusb_open_device_with_vid_pid.argtypes = [
    ctypes.c_void_p,
    ctypes.c_uint16,
    ctypes.c_uint16,
]
libusb.libusb_open_device_with_vid_pid.restype = ctypes.c_void_p

libusb.libusb_close.argtypes = [ctypes.c_void_p]
libusb.libusb_close.restype = None

libusb.libusb_claim_interface.argtypes = [ctypes.c_void_p, ctypes.c_int]
libusb.libusb_claim_interface.restype = ctypes.c_int

libusb.libusb_release_interface.argtypes = [ctypes.c_void_p, ctypes.c_int]
libusb.libusb_release_interface.restype = ctypes.c_int

libusb.libusb_clear_halt.argtypes = [ctypes.c_void_p, ctypes.c_ubyte]
libusb.libusb_clear_halt.restype = ctypes.c_int

libusb.libusb_bulk_transfer.argtypes = [
    ctypes.c_void_p,
    ctypes.c_ubyte,
    ctypes.POINTER(ctypes.c_ubyte),
    ctypes.c_int,
    ctypes.POINTER(ctypes.c_int),
    ctypes.c_uint,
]
libusb.libusb_bulk_transfer.restype = ctypes.c_int

libusb.libusb_kernel_driver_active.argtypes = [ctypes.c_void_p, ctypes.c_int]
libusb.libusb_kernel_driver_active.restype = ctypes.c_int

libusb.libusb_detach_kernel_driver.argtypes = [ctypes.c_void_p, ctypes.c_int]
libusb.libusb_detach_kernel_driver.restype = ctypes.c_int


def unlock() -> bool:
    ctx = ctypes.c_void_p()
    ret = libusb.libusb_init(ctypes.byref(ctx))
    if ret != 0:
        print(f"Error: libusb_init failed with code {ret}", file=sys.stderr)
        return False

    vid, pid = 0x07CF, 0x6101
    handle = libusb.libusb_open_device_with_vid_pid(ctx, vid, pid)
    if not handle:
        print(
            "Error: calculator not found or permission denied. Run with sudo.",
            file=sys.stderr,
        )
        libusb.libusb_exit(ctx)
        return False

    try:
        if libusb.libusb_kernel_driver_active(handle, 0) == 1:
            libusb.libusb_detach_kernel_driver(handle, 0)

        ret = libusb.libusb_claim_interface(handle, 0)
        if ret != 0:
            print(f"Error: claim_interface failed with code {ret}", file=sys.stderr)
            return False

        libusb.libusb_clear_halt(handle, 0x82)
        libusb.libusb_clear_halt(handle, 0x01)

        transferred = ctypes.c_int(0)
        buf = (ctypes.c_ubyte * 64)()

        # Handshake step 1: ENQ
        req1 = b"\x0500070"
        c_req1 = (ctypes.c_ubyte * len(req1))(*req1)
        ret = libusb.libusb_bulk_transfer(
            handle, 0x01, c_req1, len(req1), ctypes.byref(transferred), 2000
        )
        if ret != 0:
            print(f"Error: sending ENQ failed with code {ret}", file=sys.stderr)
            return False

        ret = libusb.libusb_bulk_transfer(
            handle, 0x82, buf, 64, ctypes.byref(transferred), 2000
        )
        resp1 = bytes(buf[: transferred.value])
        if ret != 0 or resp1 != b"\x0600070":
            print(f"Error: unexpected response to ENQ: {resp1}", file=sys.stderr)
            return False

        # Handshake step 2: CAN (unlock)
        req2 = b"\x1800070"
        c_req2 = (ctypes.c_ubyte * len(req2))(*req2)
        ret = libusb.libusb_bulk_transfer(
            handle, 0x01, c_req2, len(req2), ctypes.byref(transferred), 2000
        )
        if ret != 0:
            print(f"Error: sending CAN failed with code {ret}", file=sys.stderr)
            return False

        ret = libusb.libusb_bulk_transfer(
            handle, 0x82, buf, 64, ctypes.byref(transferred), 2000
        )
        resp2 = bytes(buf[: transferred.value])
        if ret != 0 or resp2 != b"\x0600070":
            print(f"Error: unexpected response to CAN: {resp2}", file=sys.stderr)
            return False

        print("Exam Mode unlocked.")
        return True

    finally:
        libusb.libusb_release_interface(handle, 0)
        libusb.libusb_close(handle)
        libusb.libusb_exit(ctx)


if __name__ == "__main__":
    success = unlock()
    sys.exit(0 if success else 1)
