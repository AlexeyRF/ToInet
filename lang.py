import ctypes
import locale

def is_english_system():
    try:
        windll = ctypes.windll.kernel32
        lang_id = windll.GetUserDefaultUILanguage()
        return (lang_id & 0xFF) == 0x09
    except Exception:
        try:
            loc = locale.getdefaultlocale()[0]
            if loc:
                return 'en' in loc.lower()
            return False
        except:
            return False

_is_en = is_english_system()

def T(ru_text, en_text):
    return en_text if _is_en else ru_text

import builtins
builtins.T = T
