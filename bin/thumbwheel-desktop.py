#!/usr/bin/env python3
"""Switch KDE virtual desktops with the MX Master thumb wheel."""
import argparse
import subprocess
import sys
import time

import evdev
from evdev import InputDevice, UInput, ecodes as e

p = argparse.ArgumentParser()
p.add_argument("--match", default="MX Master 3S", help="substring of the input device name")
p.add_argument("--threshold", type=int, default=120,
               help="hi-res units per desktop switch (120 = one wheel detent)")
p.add_argument("--cooldown", type=float, default=0.25, help="seconds to ignore input after a switch")
p.add_argument("--idle", type=float, default=0.4,
               help="reset accumulated movement after this many idle seconds")
p.add_argument("--invert", action="store_true", help="swap left/right")
p.add_argument("--grab", action="store_true",
               help="grab the mouse and forward everything except thumb wheel events "
                    "(stops horizontal scrolling in apps; needs /dev/uinput access)")
p.add_argument("--list", action="store_true", help="list input devices and exit")
args = p.parse_args()

if args.list:
    for path in evdev.list_devices():
        d = InputDevice(path)
        print(path, d.name)
    sys.exit(0)


def find_device():
    for path in evdev.list_devices():
        d = InputDevice(path)
        rel = d.capabilities().get(e.EV_REL, [])
        if args.match.lower() in d.name.lower() and (
            e.REL_HWHEEL in rel or e.REL_HWHEEL_HI_RES in rel
        ):
            return d
    return None


dev = find_device()
if dev is None:
    sys.exit(f"No device matching '{args.match}' with a horizontal wheel found (try --list)")

has_hires = e.REL_HWHEEL_HI_RES in dev.capabilities().get(e.EV_REL, [])
print(f"Using {dev.path}: {dev.name} (hi-res: {has_hires})", flush=True)

ui = None
if args.grab:
    ui = UInput.from_device(dev, name="thumbwheel-desktop passthrough")
    dev.grab()


def switch(direction):
    name = "Switch One Desktop to the Right" if direction > 0 else "Switch One Desktop to the Left"
    subprocess.Popen(
        ["gdbus", "call", "--session",
         "--dest", "org.kde.kglobalaccel",
         "--object-path", "/component/kwin",
         "--method", "org.kde.kglobalaccel.Component.invokeShortcut", name],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )


acc = 0
last_event = 0.0
cooldown_until = 0.0

try:
    for ev in dev.read_loop():
        is_wheel = ev.type == e.EV_REL and ev.code in (e.REL_HWHEEL, e.REL_HWHEEL_HI_RES)
        if not is_wheel:
            if ui:
                ui.write_event(ev)
            continue

        # Use hi-res events if the device has them, otherwise whole detents.
        if ev.code == e.REL_HWHEEL_HI_RES:
            units = ev.value
        elif not has_hires:
            units = ev.value * 120
        else:
            continue
        if args.invert:
            units = -units

        now = time.monotonic()
        if now < cooldown_until:
            continue
        if now - last_event > args.idle:
            acc = 0
        last_event = now
        if acc and (acc > 0) != (units > 0):
            acc = 0  # direction change
        acc += units

        if abs(acc) >= args.threshold:
            switch(1 if acc > 0 else -1)
            acc = 0
            cooldown_until = now + args.cooldown
except OSError as err:  # mouse went to sleep / disconnected
    sys.exit(f"Device lost: {err}")
finally:
    if args.grab:
        try:
            dev.ungrab()
        except OSError:
            pass


