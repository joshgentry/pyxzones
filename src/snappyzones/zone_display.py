
from Xlib import X, Xutil, Xatom
from Xlib.ext import shape
from ewmh import EWMH

from .zoning import ZoneProfile


class OutlineWindow:
    def __init__(self, display, x, y, w, h, lw=3):
        self.d = display
        self.screen = self.d.screen()

        self.WM_DELETE_WINDOW = self.d.intern_atom('WM_DELETE_WINDOW')
        self.WM_PROTOCOLS = self.d.intern_atom('WM_PROTOCOLS')

        # Creates a pixel map that will be used to draw the areas that aren't masked
        bgpm = self.screen.root.create_pixmap(1, 1, self.screen.root_depth)

        # In my case I chose the color of the rectangle to be red.
        bggc = self.screen.root.create_gc(
            foreground=0x7777ff,
            background=self.screen.black_pixel
        )

        # we fill the pixel map with red 
        bgpm.fill_rectangle(bggc, 0, 0, 1, 1)
        geometry = self.screen.root.get_geometry()

        # We then create a window with the background pixel map from above (a red window)
        self.window = self.screen.root.create_window(
            0, 0, geometry.width, geometry.height, 0,
            self.screen.root_depth,
            X.InputOutput,
            X.CopyFromParent,
            background_pixmap=bgpm,
            event_mask=X.StructureNotifyMask,
            colormap=X.CopyFromParent,
        )

        # We want to make sure we're notified of window destruction so we need to enable this protocol
        self.window.set_wm_protocols([self.WM_DELETE_WINDOW])
        self.window.set_wm_hints(flags=Xutil.StateHint, initial_state=Xutil.NormalState)

        # Create an outer rectangle that will be the outer edge of the visible rectangle
        outer_rect = self.window.create_pixmap(w, h, 1)
        gc = outer_rect.create_gc(foreground=1, background=0)
        # coordinates within the graphical context are always relative to itself - not the screen!
        outer_rect.fill_rectangle(gc, 0, 0, w, h)
        gc.free()

        # Create an inner rectangle that is slightly smaller to represent the inner edge of the rectangle
        inner_rect = self.window.create_pixmap(w - (lw * 2), h - (lw * 2), 1)
        gc = inner_rect.create_gc(foreground=1, background=0)
        inner_rect.fill_rectangle(gc, 0, 0, w - (lw * 2), h - (lw * 2))
        gc.free()

        # First add the outer rectangle within the window at x y coordinates
        self.window.shape_mask(shape.SO.Set, shape.SK.Bounding, x, y, outer_rect)

        # Now subtract the inner rectangle at the same coordinates + line width from the outer rect
        # This creates a red rectangular outline that can be clicked through
        self.window.shape_mask(shape.SO.Subtract, shape.SK.Bounding, x + lw, y + lw, inner_rect)
        self.window.shape_select_input(0)
        self.window.map()
        
        # use the python-ewmh lib to set extended attributes on the window. Make sure to do this after
        # calling window.map() otherwise your attributes will not be received by the window.
        self.ewmh = EWMH(display, self.screen.root)

        # Always on top
        self.ewmh.setWmState(self.window, 1, '_NET_WM_STATE_ABOVE')

        # Dock is interpreted like a panel, no borders and won't cause other panels to vanish (like fullscreen)
        wm_window_type = display.intern_atom('_NET_WM_WINDOW_TYPE')
        wm_window_type_dock = display.intern_atom('_NET_WM_WINDOW_TYPE_DOCK')
        self.window.change_property(wm_window_type, Xatom.ATOM, 32, [wm_window_type_dock], X.PropModeReplace)

        # Don't show the icon in the task bar
        self.ewmh.setWmState(self.window, 1, '_NET_WM_STATE_SKIP_TASKBAR')
        self.ewmh.setWmState(self.window, 1, '_NET_WM_STATE_SKIP_PAGER')

        #self.ewmh.setWmState(self.window, 1, '_MOTIF_WM_HINTS')

        # Apply changes
        display.flush()


    # Main loop, handling events
    def loop(self):
        while True:
            e = self.d.next_event()

            # Window has been destroyed, quit
            if e.type == X.DestroyNotify:
                break

            # Somebody wants to tell us something
            elif e.type == X.ClientMessage:
                if e.client_type == self.WM_PROTOCOLS:
                    fmt, data = e.data
                    if fmt == 32 and data[0] == self.WM_DELETE_WINDOW:
                        break

#if __name__ == '__main__':
#    OutlineWindow(display.Display(), 0, 0, 200, 200).loop()

def setup(xdisplay, zp: ZoneProfile):

    # find available space (no panels)
    from collections import namedtuple
    WorkArea = namedtuple('WorkArea', 'x y width height')
    work_area_property = xdisplay.screen().root.get_full_property(xdisplay.intern_atom('_NET_WORKAREA'), Xatom.CARDINAL)
    print(f"{work_area_property.value=}")
    # work_area_property.value is a list of desktops of repeating x,y,w,h specs
    # this includes virtual desktops, tbd on what this means for multi-monitor
    work_area = WorkArea(*work_area_property.value[:4])
    print(f"{work_area=}")

    # todo: multi-monitors
    # todo: lw border too thick on bottom, gets cut off by panel
    # todo: not a problem, but window size shouldn't be larger than render size, no need
    # todo: don't make one window-per-zone if it can be avoided, just one and draw zones in it

    # todo: move this safe-zone logic to zp.zones definition
    # (right now window resizing won't use the safe zone [!])
    for zone in zp.zones:
        print(f"{zone.x=}, {zone.y=}, {zone.width=}, {zone.height=}")
        #OutlineWindow(xdisplay, zone.x, zone.y-1156, zone.width, zone.height)
        OutlineWindow(
            xdisplay,
            zone.x if zone.x >= work_area.x else work_area.x,
            zone.y if zone.y >= work_area.y else work_area.y,
            zone.width if zone.width <= work_area.width else work_area.width,
            zone.height if zone.height <= work_area.height else work_area.height,
        )
