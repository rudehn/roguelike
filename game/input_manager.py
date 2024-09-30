from tcod.event import get_keyboard_state, get_mouse_state, KeySym, MouseButton

class InputManager:
    def __init__(self):
        self.keys_just_pressed: set[KeySym] = set()
        self._mouse_moved: bool = False

    def clear(self):
        self.keys_just_pressed.clear()
        self.mouse_moved = False

    def add_key_just_pressed(self, key: KeySym):
        self.keys_just_pressed.add(key)

    def is_key_just_pressed(self, key: KeySym):
        return key in self.keys_just_pressed

    def is_any_key_just_pressed(self):
        return len(self.keys_just_pressed) > 0

    @property
    def mouse_moved(self):
        return self._mouse_moved

    @mouse_moved.setter
    def mouse_moved(self, moved: bool):
        self._mouse_moved = moved

    def is_key_pressed(self, key: KeySym):
        """Is the state of the key currently pressed"""
        state = get_keyboard_state()
        return state[key.scancode]

    def is_mouse_pressed(self, btn: MouseButton):
        state = get_mouse_state()
        return False
        # return state.state & btn

    @property
    def cursor_location(self):
        state = get_mouse_state()
        return state.position
