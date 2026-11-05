#!/usr/bin/env python3
"""MX Master: thumb wheel switches KDE desktops, scroll wheel sends Up/Down arrows."""
import argparse
import subprocess
import sys
import time

import evdev
from evdev import InputDevice, UInput, ecodes as e

p = argparse.ArgumentParser()
p.add_argument("--match", default="MX Master 3S", help="substring of the input device name")
p.add_argument("--threshold", type=int, default=120,
               help="thumb wheel: hi-res units per desktop switch (120 = one detent)")
p.add_argument("--cooldown", type=float, default=0.25,
               help="thumb wheel: seconds to ignore input after a switch")
p.add_argument("--idle", type=float, default=0.4,
               help="reset accumulated movement after this many idle seconds")
p.add_argument("--invert", action="store_true", help="thumb wheel: swap left/right")
p.add_argument("--scroll-arrows", action="store_true",
               help="turn the scroll wheel into Up/Down arrow key presses (requires --grab)")
p.add_argument("--scroll-threshold", type=int, default=120,
               help="scroll wheel: hi-res units per arrow press (120 = one detent)")
p.add_argument("--scroll-invert", action="store_true", help="scroll wheel: swap Up/Down")
p.add_argument("--grab", action="store_true",
               help="grab the mouse and forward everything except the wheel events handled here "
                    "(needs /dev/uinput access)")
p.add_argument("--list", action="store_true", help="list input devices and exit")
args = p.parse_args()

if args.list:
    for path in evdev.list_devices():
        print(path, InputDevice(path).name)
    sys.exit(0)

if args.scroll_arrows and not args.grab:
    sys.exit("--scroll-arrows needs --grab (otherwise apps would get scroll AND arrows)")


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

rel_caps = dev.capabilities().get(e.EV_REL, [])
has_hires_h = e.REL_HWHEEL_HI_RES in rel_caps
has_hires_v = e.REL_WHEEL_HI_RES in rel_caps
print(f"Using {dev.path}: {dev.name} (hi-res h/v: {has_hires_h}/{has_hires_v})", flush=True)

ui = None   # passthrough copy of the mouse
kb = None   # virtual keyboard for the arrow keys
if args.grab:
    ui = UInput.from_device(dev, name="thumbwheel-desktop passthrough")
    if args.scroll_arrows:
        kb = UInput({e.EV_KEY: [e.KEY_UP, e.KEY_DOWN]}, name="thumbwheel-desktop arrows")
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


def press(key):
    kb.write(e.EV_KEY, key, 1)
    kb.syn()
    kb.write(e.EV_KEY, key, 0)
    kb.syn()


class Accumulator:
    """Sums wheel units; resets on idle or direction change."""

    def __init__(self, idle):
        self.idle = idle
        self.acc = 0
        self.last = 0.0

    def add(self, units, now):
        if now - self.last > self.idle:
            self.acc = 0
        self.last = now
        if self.acc and (self.acc > 0) != (units > 0):
            self.acc = 0
        self.acc += units
        return self.acc


h_acc = Accumulator(args.idle)
v_acc = Accumulator(args.idle)
h_cooldown_until = 0.0

H_CODES = (e.REL_HWHEEL, e.REL_HWHEEL_HI_RES)
V_CODES = (e.REL_WHEEL, e.REL_WHEEL_HI_RES)


def units_for(ev, hires_code, lowres_code, has_hires):
    """Hi-res units for one event, or None if it should be ignored (duplicate)."""
    if ev.code == hires_code:
        return ev.value
    if ev.code == lowres_code and not has_hires:
        return ev.value * 120
    return None


try:
    for ev in dev.read_loop():
        now = time.monotonic()

        # ---- thumb wheel -> desktop switch ----
        if ev.type == e.EV_REL and ev.code in H_CODES:
            units = units_for(ev, e.REL_HWHEEL_HI_RES, e.REL_HWHEEL, has_hires_h)
            if units is None or now < h_cooldown_until:
                continue
            if args.invert:
                units = -units
            total = h_acc.add(units, now)
            if abs(total) >= args.threshold:
                switch(1 if total > 0 else -1)
                h_acc.acc = 0
                h_cooldown_until = now + args.cooldown
            continue

        # ---- scroll wheel -> Up/Down arrows ----
        if args.scroll_arrows and ev.type == e.EV_REL and ev.code in V_CODES:
            units = units_for(ev, e.REL_WHEEL_HI_RES, e.REL_WHEEL, has_hires_v)
            if units is None:
                continue
            if args.scroll_invert:
                units = -units
            total = v_acc.add(units, now)
            steps = int(total / args.scroll_threshold)  # truncates toward zero
            if steps:
                v_acc.acc -= steps * args.scroll_threshold
                key = e.KEY_UP if steps > 0 else e.KEY_DOWN  # wheel away from you = up
                for _ in range(abs(steps)):
                    press(key)
            continue

        # ---- everything else passes through ----
        if ui:
            ui.write_event(ev)
except OSError as err:  # mouse went to sleep / disconnected
    sys.exit(f"Device lost: {err}")
finally:
    if args.grab:
        try:
            dev.ungrab()
        except OSError:
            pass

