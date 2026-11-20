#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
ByeByeDPI Strategy Tester GUI (Standalone & Full-featured)
==========================================================
Self-contained utility to test ByeDPI (ciadpi) circumvention strategies 
against selected domain lists (including official YouTube & GoogleVideo CDN lists 
from romanvht/ByeByeDPI repository).
"""

import sys
import os
import time
import json
import socket
import ssl
import http.client
import urllib.parse
import subprocess
import struct
import shutil
from concurrent.futures import ThreadPoolExecutor, as_completed

from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QLabel, QLineEdit, QPushButton, 
                             QListWidget, QListWidgetItem, QTableWidget, QTableWidgetItem, 
                             QHeaderView, QProgressBar, QSpinBox, QDoubleSpinBox, 
                             QGroupBox, QFileDialog, QMessageBox, QTabWidget)
from PySide6.QtGui import QIcon, QFont, QColor
from PySide6.QtCore import Qt, QThread, Signal

# Base Directory Resolution
_parent = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _parent not in sys.path:
    sys.path.insert(0, _parent)
try:
    from managers.system_utils import get_base_dir
    SCRIPT_DIR = get_base_dir()
except Exception:
    if getattr(sys, 'frozen', False):
        SCRIPT_DIR = os.path.dirname(sys.executable)
    else:
        SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# C++ ML Optimizer Bridge (bin/zdpi_ml_optimizer.exe)
class ZDPIMLOptimizer:
    """Bridge for the C++ zDPI ML Strategy Optimizer binary"""
    def __init__(self, history_file=None):
        self.exe_path = self._find_exe()
        self.history_file = history_file or self._resolve_history_file()
        self.history = []
        self.top_features = []
        self.load_history()
        self.train_model()

    def _find_exe(self):
        candidates = [
            os.path.join(SCRIPT_DIR, "bin", "zdpi_ml_optimizer.exe"),
            os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "bin", "zdpi_ml_optimizer.exe"),
            os.path.join(os.getcwd(), "bin", "zdpi_ml_optimizer.exe"),
        ]
        if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
            candidates.insert(0, os.path.join(sys._MEIPASS, "bin", "zdpi_ml_optimizer.exe"))
        for c in candidates:
            if os.path.exists(c):
                return os.path.abspath(c)
        return None

    def _resolve_history_file(self):
        candidates = [
            os.path.join(SCRIPT_DIR, "ui", "zdpi_ml_history.json"),
            os.path.join(os.path.dirname(os.path.abspath(__file__)), "zdpi_ml_history.json"),
            os.path.join(SCRIPT_DIR, "data", "zdpi_ml_history.json"),
        ]
        for c in candidates:
            if os.path.exists(c):
                return os.path.abspath(c)
        return os.path.join(SCRIPT_DIR, "ui", "zdpi_ml_history.json")

    def load_history(self):
        if self.history_file and os.path.exists(self.history_file):
            try:
                with open(self.history_file, 'r', encoding='utf-8') as f:
                    self.history = json.load(f)
                    return True
            except Exception:
                pass
        self.history = []
        return False

    def add_result(self, strategy, overall_pct, pri_pct, ok_cnt, tot_cnt, details=None):
        if not self.exe_path or not os.path.exists(self.exe_path):
            return False
        try:
            cmd = [
                self.exe_path,
                "add",
                strategy,
                str(float(overall_pct)),
                str(float(pri_pct)),
                str(int(ok_cnt)),
                str(int(tot_cnt))
            ]
            flags = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
            res = subprocess.run(cmd, capture_output=True, text=True, creationflags=flags, timeout=5)
            self.load_history()
            return res.returncode == 0
        except Exception as e:
            print(f"[zDPI ML Bridge] add_result error: {e}")
            return False

    def train_model(self):
        if not self.exe_path or not os.path.exists(self.exe_path):
            return False
        try:
            flags = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
            cmd = [self.exe_path, "top-features"]
            res = subprocess.run(cmd, capture_output=True, text=True, creationflags=flags, timeout=5)
            if res.returncode == 0:
                features = []
                for line in res.stdout.strip().splitlines():
                    parts = line.strip().split("\t")
                    if len(parts) == 2:
                        try:
                            features.append((parts[0].strip(), float(parts[1].strip())))
                        except ValueError:
                            pass
                self.top_features = features
            self.load_history()
            return True
        except Exception as e:
            print(f"[zDPI ML Bridge] train_model error: {e}")
            return False

    def generate_ai_strategies(self, count=15, existing_strategies=None):
        if not self.exe_path or not os.path.exists(self.exe_path):
            return []
        try:
            flags = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
            temp_file = None
            cmd = [self.exe_path, "generate", str(count)]
            if existing_strategies:
                import tempfile
                with tempfile.NamedTemporaryFile('w', delete=False, encoding='utf-8', suffix='.txt') as tf:
                    temp_file = tf.name
                    for s in existing_strategies:
                        tf.write(s.strip() + "\n")
                cmd.append(temp_file)

            res = subprocess.run(cmd, capture_output=True, text=True, creationflags=flags, timeout=10)
            if temp_file and os.path.exists(temp_file):
                try: os.remove(temp_file)
                except Exception: pass

            if res.returncode == 0:
                out = res.stdout.strip()
                start = out.find('[')
                end = out.rfind(']')
                if start != -1 and end != -1:
                    return json.loads(out[start:end+1])
            return []
        except Exception as e:
            print(f"[zDPI ML Bridge] generate_ai_strategies error: {e}")
            return []

    def predict_score(self, strategy):
        if not self.exe_path or not os.path.exists(self.exe_path):
            return 50.0
        try:
            flags = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
            res = subprocess.run([self.exe_path, "predict", strategy], capture_output=True, text=True, creationflags=flags, timeout=3)
            if res.returncode == 0:
                return float(res.stdout.strip())
        except Exception:
            pass
        return 50.0

    def explain_recommendation(self, strategy):
        if not self.exe_path or not os.path.exists(self.exe_path):
            return ""
        try:
            flags = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
            res = subprocess.run([self.exe_path, "explain", strategy], capture_output=True, text=True, creationflags=flags, timeout=3)
            if res.returncode == 0:
                return res.stdout.strip()
        except Exception:
            pass
        return ""

HAS_SKLEARN = True
if not ZDPIMLOptimizer().exe_path:
    ZDPIMLOptimizer = None

# Optional ToInet-MAX integration fallbacks
try:
    from managers import system_utils as lang
except ImportError:
    lang = None

def T(ru: str, en: str = "") -> str:
    if lang and hasattr(lang, "T"):
        try:
            return lang.T(ru, en)
        except Exception:
            pass
    return ru

try:
    from managers import config_manager
except ImportError:
    config_manager = None

# Smart binary locator
def find_ciadpi_executable():
    candidates = [
        os.path.join(SCRIPT_DIR, "zdpi.exe"),
        os.path.join(SCRIPT_DIR, "ciadpi.exe"),
        os.path.join(SCRIPT_DIR, "byedpi", "zdpi.exe"),
        os.path.join(SCRIPT_DIR, "byedpi", "ciadpi.exe"),
        os.path.join(os.path.dirname(SCRIPT_DIR), "byedpi", "zdpi.exe"),
        os.path.join(os.path.dirname(SCRIPT_DIR), "byedpi", "ciadpi.exe"),
        os.path.join(os.path.dirname(SCRIPT_DIR), "zdpi.exe"),
        r"C:\Program Files\zdpi\zdpi.exe",
        r"C:\Program Files\byedpi\ciadpi.exe",
        r"C:\Program Files (x86)\byedpi\ciadpi.exe",
    ]
    which_bin = shutil.which("zdpi.exe") or shutil.which("ciadpi.exe") or shutil.which("ciadpi")
    if which_bin:
        candidates.insert(0, which_bin)
    for c in candidates:
        if os.path.isfile(c):
            return os.path.normpath(c)
    return os.path.join(SCRIPT_DIR, "zdpi.exe")

BYEDPI_EXE_DEFAULT = find_ciadpi_executable()

# Configuration / Data text files
SITES_FILE = os.path.join(SCRIPT_DIR, "byedpi_tester_sites.txt")
STRATEGIES_FILE = os.path.join(SCRIPT_DIR, "byedpi_tester_strategies.txt")
PRIORITY_SITES_FILE = os.path.join(SCRIPT_DIR, "byedpi_tester_priority_sites.txt")

# If files don't exist in SCRIPT_DIR, check byedpi subfolder
if not os.path.exists(SITES_FILE) and os.path.exists(os.path.join(SCRIPT_DIR, "byedpi", "byedpi_tester_sites.txt")):
    SITES_FILE = os.path.join(SCRIPT_DIR, "byedpi", "byedpi_tester_sites.txt")
if not os.path.exists(STRATEGIES_FILE) and os.path.exists(os.path.join(SCRIPT_DIR, "byedpi", "byedpi_tester_strategies.txt")):
    STRATEGIES_FILE = os.path.join(SCRIPT_DIR, "byedpi", "byedpi_tester_strategies.txt")
if not os.path.exists(PRIORITY_SITES_FILE) and os.path.exists(os.path.join(SCRIPT_DIR, "byedpi", "byedpi_tester_priority_sites.txt")):
    PRIORITY_SITES_FILE = os.path.join(SCRIPT_DIR, "byedpi", "byedpi_tester_priority_sites.txt")


# --- Lists from ByeByeDPI Repository ---
YOUTUBE_SITES = [
    "youtube.com",
    "youtu.be",
    "www.youtube.com",
    "i.ytimg.com",
    "i9.ytimg.com",
    "yt3.ggpht.com",
    "yt4.ggpht.com",
    "googleapis.com",
    "jnn-pa.googleapis.com",
    "googleusercontent.com",
    "signaler-pa.youtube.com",
    "youtubei.googleapis.com",
    "manifest.googlevideo.com",
    "yt3.googleusercontent.com"
]

GOOGLEVIDEO_SITES = [
    "rr1---sn-4axm-n8vs.googlevideo.com",
    "rr1---sn-gvnuxaxjvh-o8ge.googlevideo.com",
    "rr1---sn-ug5onuxaxjvh-p3ul.googlevideo.com",
    "rr1---sn-ug5onuxaxjvh-n8v6.googlevideo.com",
    "rr4---sn-q4flrnsl.googlevideo.com",
    "rr10---sn-gvnuxaxjvh-304z.googlevideo.com",
    "rr14---sn-n8v7kn7r.googlevideo.com",
    "rr16---sn-axq7sn76.googlevideo.com",
    "rr1---sn-8ph2xajvh-5xge.googlevideo.com",
    "rr1---sn-gvnuxaxjvh-5gie.googlevideo.com",
    "rr12---sn-gvnuxaxjvh-bvwz.googlevideo.com",
    "rr5---sn-n8v7knez.googlevideo.com",
    "rr1---sn-u5uuxaxjvhg0-ocje.googlevideo.com",
    "rr2---sn-q4fl6ndl.googlevideo.com",
    "rr5---sn-gvnuxaxjvh-n8vk.googlevideo.com",
    "rr4---sn-jvhnu5g-c35d.googlevideo.com",
    "rr1---sn-q4fl6n6y.googlevideo.com",
    "rr2---sn-hgn7ynek.googlevideo.com",
    "rr1---sn-xguxaxjvh-gufl.googlevideo.com"
]

GENERAL_SITES = [
    "rutracker.org",
    "nyaa.si",
    "rutor.org",
    "nnmclub.to",
    "speedtest.net"
]

DEFAULT_SITES = GENERAL_SITES + YOUTUBE_SITES + GOOGLEVIDEO_SITES

# --- Embedded Curated Strategies (zDPI / Zapret2 & ByeDPI) ---
DEFAULT_STRATEGIES = [
    '--dpi-desync=fake,split2 --dpi-desync-split-pos=midsld --dpi-desync-fake-tls=google --dpi-desync-ttl=3 --quic-drop',
    '--dpi-desync=fake,split2 --dpi-desync-split-pos=midsld --dpi-desync-fake-tls=kyber --dpi-desync-ttl=3 --quic-drop',
    '--dpi-desync=fake,disorder2 --dpi-desync-split-pos=1 --dpi-desync-ttl=3 --quic-drop',
    '--dpi-desync=fake,split2 --dpi-desync-split-pos=sniext --dpi-desync-fake-tls=google --dpi-desync-ttl=3 --quic-drop',
    '--dpi-desync=fake,multisplit --dpi-desync-split-pos=1,midsld --dpi-desync-fake-tls=kyber --dpi-desync-ttl=4 --quic-drop',
    '--dpi-desync=fakedsplit --dpi-desync-split-pos=midsld --dpi-desync-ttl=3 --quic-drop',
    '--dpi-desync=fake,tlsrec --dpi-desync-split-pos=midsld --dpi-desync-fake-tls=google --dpi-desync-ttl=3 --quic-drop',
    '--dpi-desync=tlsrec --dpi-desync-split-pos=midsld --quic-drop',
    '--dpi-desync=fake,disorder2 --dpi-desync-split-pos=midsld --dpi-desync-fake-tls=google --dpi-desync-ttl=2 --quic-drop',
    '--dpi-desync=fake,split2 --dpi-desync-split-pos=sni --dpi-desync-fake-tls=rutracker --dpi-desync-ttl=3 --quic-drop',
    '--dpi-desync=fake,multisplit --dpi-desync-split-pos=1,sniext,midsld --dpi-desync-fake-tls=google --dpi-desync-ttl=3 --quic-drop',
    '--dpi-desync=fake,disorder --dpi-desync-split-pos=sniext --dpi-desync-fake-tls=kyber --dpi-desync-ttl=3 --quic-drop',
    '-s midsld -f midsld -r midsld -t 3 --quic-drop',
    '-s sniext -f 1 -r sniext -t 4 --quic-drop',
    '-d midsld -f 1 -t 3 --quic-drop',
    '-f-200 -Qr -s3:5+sm -a1 -As -d1 -s4+sm -s8+s -f-300 -d6+s -a1 -At,r,s -o2 -f-30 -As -r5 -Mh -r6+s -f-250 -s2:7+s -s3:6+sm -a1 -At,r,s -s3:5+sm -s6+s -s7:9+s -q30+sm -a1',
    '-d1 -d3+s -s6+s -d9+s -s12+s -d15+s -s20+s -d25+s -s30+s -d35+s -r1+s -a1 -As -d1 -d3+s -s6+s -d9+s -s12+s -d15+s -s20+s -d25+s -s30+s -d35+s -a1',
    '-q2 -s2 -s3+s -r3 -s4 -r4 -s5+s -r5+s -s6 -s7+s -r8 -s9+s -Qr -Mh,d,r -a1 -At,r -s2+s -r2 -d2 -s3 -r3 -r4 -s4 -d5+s -r5 -d6 -s7+s -d7 -a1',
    '-o1 -d1 -a1 -At,r,s -s1 -d1 -s5+s -s10+s -s15+s -s20+s -r1+s -a1 -As -s1 -d1 -s5+s -s10+s -s15+s -s20+s -a1',
    '-n {sni} -Qr -f-204 -s1:5+sm -a1 -As -d1 -s3+s -s5+s -q7 -a1 -As -o2 -f-43 -a1 -As -r5 -Mh -s1:5+s -s3:7+sm -a1',
    '-n {sni} -Qr -f-205 -a1 -As -s1:3+sm -a1 -As -s5:8+sm -a1 -As -d3 -q7 -o2 -f-43 -f-85 -f-165 -r5 -Mh -a1',
    '-d1+s -s50+s -a1 -As -f20 -r2+s -a1 -At -d2 -s1+s -s5+s -s10+s -s15+s -s25+s -s35+s -s50+s -s60+s -a1',
    '-o1 -a1 -At,r,s -f-1 -a1 -At,r,s -d1:11+sm -a1 -At,r,s -n {sni} -Qr -f1 -d1:11+sm -s1:11+sm -a1',
    '-d1 -s1 -q1 -a1 -Ar -s5 -o1+s -d3+s -s6+s -d9+s -s12+s -d15+s -s20+s -d25+s -s30+s -d35+s -a1',
    '-f1+nm -t6 -a1 -As -n {sni} -Qr -s1:6+sm -a1 -As -s5:12+sm -a1 -As -d3 -q7 -r6 -Mh -a1',
    '-d1 -s1+s -d3+s -s6+s -d9+s -s12+s -d15+s -s20+s -d25+s -s30+s -d35+s -a1',
    '-d1 -s1+s -d1+s -s3+s -d6+s -s12+s -d14+s -s20+s -d24+s -s30+s -a1',
    '-o1 -a1 -At,r,s -f-1 -a1 -Ar,s -o1 -a1 -At -r1+s -f-1 -t6 -a1',
    '-d1 -s1+s -s3+s -s6+s -s9+s -s12+s -s15+s -s20+s -s30+s -a1',
    '-d1 -d3+s -s6+s -d6+s -s7+s -d8+s -s10+s -a1 -t12 -At,s -r3',
    '-f1 -t5 -n {sni} -q3+h -Qr -f2 -q1 -r1+s -t15 -q1 -o2 -a1',
    '-n {sni} -d2:5:2+h -f-3 -r2+sm -o2 -o50+s -r2+s -f-4 -a1',
    '-f-1 -Qr -s1+sm -d3+s -s5+sm -o2 -a1 -As -r1+s -d8+s -a1',
    '-r-1+s -o20+sm -s3:7+sm -d5:3+sm -f300+s -Qr -f-1 -a1',
    '-o2 -O4 -s1 -q1 -a1 -Ar -s5 -o1+s -f1+s -r20+s -a1',
    '-o1 -r-5+se -a1 -At,r,s -d1 -n {sni} -Qr -f-1 -a1',
    '--fake -1 --ttl 8 --split 1+s --disorder 3+s -a1',
    '-n {sni} -Qr -f6+nr -d2 -d11 -f9+hm -o3 -t7 -a1',
    '-r5+s -s25+s -a1 -At,r,s -s50 -r5+s -s50+s -a1',
    '-d1 -d3+s -s6+s -d9+s -s20+s -d25+s -s30+s -a1',
    '-d9+s -q20+s -s25+s -t5 -a1 -At,r,s -r1+h -a1',
    '-q1+s -s29+s -s30+s -s14+s -o5+s -f-1 -a1',
    '-d1 -s1+s -r1+s -e1 -m1 -o1+s -f-1 -t2 -a1',
    '-d1 -o1 -a1 -Ar -o1 -a1 -At -f-1 -r1+s -a1',
    '-d1 -s4 -d8 -s1+s -d5+s -s10+s -d20+s -a1',
    '-f-1 -n {sni} -Qr -s2+s -r3 -o20 -t4 -a1',
    '-n {sni} -Qr -d5+sm -f3+sm -o2 -t4 -a1',
    '-o1 -a1 -Ar -q1 -a1 -At -f-1 -r1+s -a1',
    '-q1 -a1 -Ar -o1 -a1 -At -f-1 -r1+s -a1',
    '-s4+s -r9+s -Qr -n {sni} -a1',
    '-o1 -d1 -r1+s -s1+s -d3+s -a1',
    '-q1+s -s29+s -o5+s -f-1 -a1',
    '-n {sni} -Qr -m2 -f-1 -d7 -a1',
    '-d1 -s1+s -r1+s -f-1 -t8 -a1',
    '-o1 -a1 -An -f1+nm -t6 -a1',
    '-n {sni} -Qr -f-1 -r1+s -a1',
    '-n {sni} -Qr -d1:3 -f-1 -a1',
    '-s1 -d3+s -a1 -At -r1+s -a1',
    '-f-1 -t8 -n {sni} -s1+s -a1',
    '-n {sni} -Qr -d1 -f-1 -a1',
    '-f64+se -n {sni} -t5 -a1',
    '-o1 -a1 -At,r,s -d1 -a1',
    '-d1+s -o2 -s5 -r5 -a1',
    '-r8 -o2 -s7 -q4+s -a1',
    '-o1 -f-1 -r-5+se -a1',
    '-d6+s -q4+hm -o2 -a1',
    '-s5+s -s35+s -m4 -a1',
    '-f-1+sm -t7 -m2 -a1',
    '-o1 -r-5+se -a1',
    '-o1+s -d3+s -a1',
    '-o1 -s4 -s6 -a1',
    '-q1 -r25+s -a1',
    '-d1 -s3+s -a1',
    '-o3 -d7 -a1',
    '-d7 -s2 -a1',
    '-l:"\\xC2\\x00\\x00\\x00\\x01\\x14\\x2E\\xE3\\xE3\\x5F\\x6B\\xBB\\x23\\xA8\\xE6\\x5D\\xA9\\x78\\x21\\xCF\\xC2\\x72\\x4C\\x8F\\xC4\\x5E\\x14\\x00\\x00\\x00\\x00\\xC5\\x00\\x00\\x00\\x00\\x4C\\x00\\xA7\\x00\\x00\\x00\\x00\\x00\\x00\\x44\\x00\\x00\\x80\\x00\\x00\\x00\\x0D\\xFC\\xFA\\x1D\\xCD\\x73\\xBA\\x2A\\x90\\x93\\xB3\\xEE\\xF7\\x43\\xC5\\x85\\xDA\\xFF\\x45\\x3C\\x00\\x00\\x00\\x00\\x00\\x00\\x7C\\x00\\x9B\\x00\\xF6\\x00\\x00\\xDD\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x59\\xA8\\xE4\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x7B\\x00\\x0F\\x00\\x00\\x00\\x48\\x4E\\x00\\x00\\x00\\x06\\xF3\\x00\\x00\\x00\\x00\\xD9\\x5A\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00" -a3 -t12 -d1 -s0+h -d3+s -s6+s -d5+s -s8+s -d7+s -s10+s -d3 -At,s -r3',
    '-f-200 -Qr -s3:5+sm -a1 -As -d1 -s4+sm -s8+sh -f-300 -d6+sh -a1 -At,r,s -o2 -f-30 -As -r5 -Mh -r6+sh -f-250 -s2:7+s -s3:6+sm -a1 -At,r,s -s3:5+sm -s6+s -s7:9+s -q30+sm -a1',
    '-Ku -l:"\\xe3\\x00\\x06\\xec\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00" -a3 -An -f64+se -n {sni} -t5',
    '-f1+nme -t6 -a1 -As -n {sni} -Qr -s1:6+sm -a1 -As -s5:12+sm -a1 -As -d3 -q7 -r6 -Mh -a1',
    '-s1 -o1 -a1 -Ar -s5 -o1+s -a1 -At -f-1 -r1+s -a1 -As -s1 -o1+s -s-1 -a1',
    '-s1 -d1 -a1 -Ar -d5 -o1+s -a1 -At -f-1 -r1+s -a1 -As -d1 -o1+s -s-1 -a1',
    '-s1 -q1 -a1 -Ar -a1 -s5 -o2 -At -f-1 -r1+s -a1 -As -s1 -o1+s -s-1 -a1',
    '-s1 -q1 -a1 -Ar -s5 -o1+s -a1 -At -f-1 -d1+s -a1 -As -s1 -o1+s -s-1 -a1',
    '-s1 -q1 -a1 -Ar -s5 -o2 -a1 -At -f-1 -r1+s -a1 -As -s1 -o1+s -s-1 -a1',
    '-s1 -q1 -a1 -At -a1 -f-1 -r1+s -a1 -As -d1+s -O1 -s29+s -a1',
    '-s25 -r5+s -s25+s -a1 -At,r,s -s50 -r5+s -s50+s -a1',
    '-o2 -O4 -s1 -q1 -a2 -Ar -s5 -o1+s -f1+s -r20+s -a2',
    '-s1 -d1 -r1+s -a1 -Ar -o1 -a1 -At -f-1 -r1+s -a1',
    '-s1 -q1 -r1+s -a1 -Ar -o1 -a1 -At -f-1 -r1+s -a1',
    '-s1 -o1 -r1+s -a1 -Ar -o1 -a1 -At -f-1 -r1+s -a1',
    '-s1 -d1 -o1 -a1 -Ar -o3 -a1 -At -f-1 -r1+s -a1',
    '-s1 -o1 -a1 -Ar -o1 -a1 -At -f-1 -r1+s -a1',
    '-s1 -q1 -a1 -At,r,s -f-1 -r1+s -a1',
    '-s1 -o1 -a1 -At,r,s -f-1 -r1+s -a1',
    '-s1 -d1 -a1 -At,r,s -f-1 -r1+s -a1',
    '-n {sni} -Qr -f209 -s1+sm -R1-3 -a1',
    '-s4+sn -r9+s -Qr -n {sni} -a1',
    '-d1 -r1+s -f-1 -t8 -o3+s -a1',
    '-o1 -a1 -An -f1+nme -t6 -a1',
    '-f-1 -t8 -n {sni} -s1+s -a5'
]

# --- STANDALONE SOCKS5 & BYEDPI PROBING ENGINE ---
def shell_split(string: str) -> list:
    tokens = []
    quote_char = ' '
    escaping = False
    quoting = False
    last_close_quote_index = -999999
    current = []

    for i in range(len(string)):
        c = string[i]
        if escaping:
            current.append(c)
            escaping = False
        elif c == '\\' and quoting:
            if i + 1 < len(string) and string[i + 1] == quote_char:
                escaping = True
            else:
                current.append(c)
        elif quoting and c == quote_char:
            quoting = False
            last_close_quote_index = i
        elif not quoting and (c == "'" or c == '"'):
            quoting = True
            quote_char = c
        elif not quoting and c.isspace():
            if current or last_close_quote_index == i - 1:
                tokens.append("".join(current))
                current = []
        else:
            current.append(c)

    if current or last_close_quote_index == len(string) - 1:
        tokens.append("".join(current))

    # Strip Linux-only unsupported flags on Windows
    if os.name == 'nt':
        tokens = [t for t in tokens if t not in ('-S', '-Y')]

    return tokens

def check_ip_and_port_in_cmd(cmd_args: list) -> tuple:
    def get_arg_value(keys: list):
        for i in range(len(cmd_args)):
            arg = cmd_args[i]
            for key in keys:
                if key.startswith("--"):
                    if arg == key and i + 1 < len(cmd_args):
                        return cmd_args[i + 1]
                    elif arg.startswith(key + "="):
                        return arg.split('=', 1)[1]
                elif key.startswith("-"):
                    if arg.startswith(key) and len(arg) > len(key):
                        return arg[len(key):]
                    elif arg == key and i + 1 < len(cmd_args):
                        return cmd_args[i + 1]
        return None

    cmd_ip = get_arg_value(["--ip", "-i"])
    cmd_port = get_arg_value(["--port", "-p"])
    return cmd_ip, cmd_port

def connect_socks5(proxy_host, proxy_port, dest_host, dest_port, timeout=5):
    s = socket.create_connection((proxy_host, proxy_port), timeout=timeout)
    s.sendall(b'\x05\x01\x00')
    resp = s.recv(2)
    if len(resp) != 2 or resp[0] != 5 or resp[1] != 0:
        s.close()
        raise Exception("SOCKS5 negotiation failed")

    try:
        ip_bytes = socket.inet_aton(dest_host)
        addr_type = 1
        addr_bytes = ip_bytes
    except socket.error:
        try:
            ip_bytes = socket.inet_pton(socket.AF_INET6, dest_host)
            addr_type = 4
            addr_bytes = ip_bytes
        except socket.error:
            addr_type = 3
            host_bytes = dest_host.encode('utf-8')
            addr_bytes = bytes([len(host_bytes)]) + host_bytes

    req = struct.pack('!BBBB', 5, 1, 0, addr_type) + addr_bytes + struct.pack('!H', dest_port)
    s.sendall(req)

    resp = s.recv(4)
    if len(resp) < 4 or resp[0] != 5 or resp[1] != 0:
        s.close()
        raise Exception(f"SOCKS5 connection failed: code {resp[1] if len(resp) >= 2 else 'unknown'}")

    bnd_addr_type = resp[3]
    if bnd_addr_type == 1:
        s.recv(6)
    elif bnd_addr_type == 3:
        len_byte = s.recv(1)
        if len_byte:
            s.recv(ord(len_byte) + 2)
    elif bnd_addr_type == 4:
        s.recv(18)

    return s

class SOCKS5HTTPConnection(http.client.HTTPConnection):
    def __init__(self, proxy_host, proxy_port, host, port=None, timeout=5, **kwargs):
        super().__init__(host, port, timeout=timeout, **kwargs)
        self.proxy_host = proxy_host
        self.proxy_port = proxy_port

    def connect(self):
        self.sock = connect_socks5(self.proxy_host, self.proxy_port, self.host, self.port or 80, self.timeout)

class SOCKS5HTTPSConnection(http.client.HTTPSConnection):
    def __init__(self, proxy_host, proxy_port, host, port=None, timeout=5, context=None, **kwargs):
        super().__init__(host, port, timeout=timeout, context=context, **kwargs)
        self.proxy_host = proxy_host
        self.proxy_port = proxy_port

    def connect(self):
        self.sock = connect_socks5(self.proxy_host, self.proxy_port, self.host, self.port or 443, self.timeout)
        if self._tunnel_host:
            self._tunnel()

        if self._context is None:
            self._context = ssl.create_default_context()
            self._context.check_hostname = False
            self._context.verify_mode = ssl.CERT_NONE

        self.sock = self._context.wrap_socket(self.sock, server_hostname=self.host)

def check_url(proxy_host, proxy_port, url_str, timeout=5):
    parsed = urllib.parse.urlparse(url_str)
    scheme = parsed.scheme.lower()
    host = parsed.hostname
    port = parsed.port
    path = parsed.path or "/"
    if parsed.query:
        path += "?" + parsed.query

    redirects_limit = 5
    current_url = url_str

    for _ in range(redirects_limit):
        if scheme == 'https':
            conn = SOCKS5HTTPSConnection(proxy_host, proxy_port, host, port or 443, timeout=timeout)
        elif scheme == 'http':
            conn = SOCKS5HTTPConnection(proxy_host, proxy_port, host, port or 80, timeout=timeout)
        else:
            return False, f"Unsupported scheme {scheme}"

        try:
            conn.request("GET", path, headers={
                "Connection": "close",
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
            })
            resp = conn.getresponse()

            declared_len = resp.getheader('content-length')
            declared_len = int(declared_len) if declared_len is not None else -1

            actual_len = 0
            limit = declared_len if declared_len > 0 else 1024 * 1024

            while actual_len < limit:
                chunk = resp.read(min(8192, limit - actual_len))
                if not chunk:
                    break
                actual_len += len(chunk)

            if resp.status in (301, 302, 303, 307, 308):
                loc = resp.getheader('Location')
                if loc:
                    current_url = urllib.parse.urljoin(current_url, loc)
                    parsed = urllib.parse.urlparse(current_url)
                    scheme = parsed.scheme.lower()
                    host = parsed.hostname
                    port = parsed.port
                    path = parsed.path or "/"
                    if parsed.query:
                        path += "?" + parsed.query
                    conn.close()
                    continue

            if declared_len <= 0 or actual_len >= declared_len:
                return True, f"Success ({resp.status})"
            else:
                return False, f"Block detected (read {actual_len} bytes, declared {declared_len})"
        except Exception as e:
            return False, str(e)
        finally:
            conn.close()

    return False, "Too many redirects"

def start_byedpi(executable, strategy_args):
    try:
        startupinfo = None
        if hasattr(subprocess, 'STARTUPINFO'):
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            startupinfo.wShowWindow = subprocess.SW_HIDE

        proc = subprocess.Popen(
            [executable] + strategy_args,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            startupinfo=startupinfo,
            text=True
        )
        return proc
    except Exception as e:
        return None

def stop_byedpi(proc):
    if proc is None:
        return
    try:
        proc.terminate()
        try:
            proc.wait(timeout=1.0)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait(timeout=1.0)
    except Exception:
        pass

def wait_for_proxy_port(proc, ip, port, timeout=4.0):
    """Waits for proxy port to open while actively monitoring process health."""
    start_time = time.time()
    while time.time() - start_time < timeout:
        # Check if the process exited prematurely
        if proc.poll() is not None:
            err = ""
            try:
                _, err_bytes = proc.communicate(timeout=0.3)
                err = err_bytes.strip()
            except Exception:
                pass
            return False, f"Ошибка ciadpi (код {proc.returncode}): {err or 'процесс аварийно завершился'}"
            
        try:
            s = socket.create_connection((ip, port), timeout=0.25)
            s.close()
            return True, "OK"
        except Exception:
            time.sleep(0.08)
            
    return False, f"Порт {ip}:{port} не открылся (таймаут {timeout} сек)"

def wait_for_port_closed(ip, port, timeout=2.5):
    """Ensures socket is fully unbound and closed before next test cycle."""
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            s = socket.create_connection((ip, port), timeout=0.15)
            s.close()
            time.sleep(0.08)
        except (socket.error, OSError):
            return True
    return False

def ensure_port_available(ip, port):
    """Cleans up any orphaned ciadpi or conflicting process occupying target port."""
    try:
        s = socket.create_connection((ip, port), timeout=0.2)
        s.close()
        if os.name == 'nt':
            for proc_name in ["zdpi.exe", "ciadpi.exe"]:
                subprocess.run(
                    ["taskkill", "/F", "/IM", proc_name],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    creationflags=subprocess.CREATE_NO_WINDOW
                )
            time.sleep(0.3)
    except (socket.error, OSError):
        pass


# --- Dark Stylesheet ---
DARK_STYLESHEET = """
QMainWindow {
    background-color: #1a1a1a;
}
QWidget {
    color: #d0d0d0;
    font-family: 'Segoe UI', Arial, sans-serif;
    font-size: 10pt;
}
QGroupBox {
    font-weight: bold;
    border: 1px solid #2d2d2d;
    border-radius: 6px;
    margin-top: 12px;
    padding: 10px;
    background-color: #222222;
}
QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    left: 10px;
    padding: 0 5px;
    color: #a0a0a0;
}
QLineEdit, QSpinBox, QDoubleSpinBox {
    background-color: #2a2a2a;
    border: 1px solid #3a3a3a;
    border-radius: 4px;
    padding: 6px;
    color: #ffffff;
}
QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus {
    border: 1px solid #555555;
}
QPushButton {
    background-color: #2d2d2d;
    border: 1px solid #3d3d3d;
    border-radius: 4px;
    padding: 6px 12px;
    color: #ffffff;
    font-weight: bold;
}
QPushButton:hover {
    background-color: #3d3d3d;
    border-color: #555555;
}
QPushButton:pressed {
    background-color: #202020;
}
QPushButton#start_btn {
    background-color: #2b3d2e;
    border-color: #3e5842;
}
QPushButton#start_btn:hover {
    background-color: #354c39;
    border-color: #4a6a50;
}
QPushButton#start_btn:disabled {
    background-color: #222222;
    color: #666666;
    border-color: #2a2a2a;
}
QPushButton#stop_btn {
    background-color: #3d2b2b;
    border-color: #583e3e;
}
QPushButton#stop_btn:hover {
    background-color: #4c3535;
    border-color: #6a4a4a;
}
QPushButton#stop_btn:disabled {
    background-color: #222222;
    color: #666666;
    border-color: #2a2a2a;
}
QPushButton#apply_btn {
    background-color: #2e3b4e;
    border-color: #3e506a;
    font-size: 11pt;
    padding: 10px;
}
QPushButton#apply_btn:hover {
    background-color: #35455c;
    border-color: #4a6182;
}
QPushButton#apply_btn:disabled {
    background-color: #222222;
    color: #666666;
    border-color: #2a2a2a;
}
QPushButton#copy_btn {
    background-color: #3a334d;
    border-color: #4e4466;
    padding: 10px;
}
QPushButton#copy_btn:hover {
    background-color: #473e5e;
    border-color: #5f537d;
}
QPushButton#copy_btn:disabled {
    background-color: #222222;
    color: #666666;
    border-color: #2a2a2a;
}
QTabWidget::pane {
    border: 1px solid #2d2d2d;
    border-radius: 6px;
    background-color: #222222;
    padding: 6px;
}
QTabBar::tab {
    background-color: #2a2a2a;
    border: 1px solid #3a3a3a;
    border-bottom: none;
    border-top-left-radius: 4px;
    border-top-right-radius: 4px;
    padding: 6px 14px;
    color: #a0a0a0;
    font-weight: bold;
    margin-right: 4px;
}
QTabBar::tab:selected {
    background-color: #222222;
    border-color: #2d2d2d;
    border-bottom: 2px solid #5a8a60;
    color: #ffffff;
}
QTabBar::tab:hover:!selected {
    background-color: #333333;
    color: #e0e0e0;
}
QListWidget {
    background-color: #222222;
    border: 1px solid #2d2d2d;
    border-radius: 6px;
    padding: 5px;
}
QListWidget::item {
    padding: 4px;
    border-bottom: 1px solid #282828;
}
QListWidget::item:selected {
    background-color: #333333;
    color: #ffffff;
    border-radius: 4px;
}
QTableWidget {
    background-color: #222222;
    border: 1px solid #2d2d2d;
    border-radius: 6px;
    gridline-color: #282828;
}
QTableWidget::item {
    padding: 5px;
}
QTableWidget::item:selected {
    background-color: #333333;
    color: #ffffff;
}
QHeaderView::section {
    background-color: #2d2d2d;
    color: #d0d0d0;
    padding: 5px;
    border: 1px solid #222222;
    font-weight: bold;
}
QProgressBar {
    border: 1px solid #2d2d2d;
    border-radius: 4px;
    text-align: center;
    background-color: #222222;
    font-weight: bold;
}
QProgressBar::chunk {
    background-color: #3a3a3a;
    border-radius: 3px;
}
QLabel#title_lbl {
    font-size: 16pt;
    font-weight: bold;
    color: #ffffff;
    padding: 5px 0px;
}
QLabel#status_desc_lbl {
    font-style: italic;
    color: #888888;
}
QScrollBar:vertical {
    border: none;
    background: #1e1e1e;
    width: 10px;
    margin: 0px 0 0px 0;
}
QScrollBar::handle:vertical {
    background: #3d3d3d;
    min-height: 20px;
    border-radius: 5px;
}
QScrollBar::handle:vertical:hover {
    background: #555555;
}
QScrollBar:horizontal {
    border: none;
    background: #1e1e1e;
    height: 10px;
    margin: 0px 0 0px 0;
}
QScrollBar::handle:horizontal {
    background: #3d3d3d;
    min-width: 20px;
    border-radius: 5px;
}
QScrollBar::handle:horizontal:hover {
    background: #555555;
}
"""

class WorkerThread(QThread):
    progress_changed = Signal(int, int, str)
    strategy_completed = Signal(str, float, int, int, dict)
    finished = Signal(list)
    error = Signal(str)

    def __init__(self, byedpi_path, strategies, sites, options):
        super().__init__()
        self.byedpi_path = byedpi_path
        self.strategies = strategies
        self.sites = sites
        self.options = options
        self.is_cancelled = False

    def run(self):
        results = []
        total = len(self.strategies)
        
        sni = self.options.get('sni', 'google.com')
        proxy_ip = self.options.get('ip', '127.0.0.1')
        proxy_port = int(self.options.get('port', 1080))
        concurrency = self.options.get('concurrency', 10)
        timeout = self.options.get('timeout', 4.0)
        delay = self.options.get('delay', 0.2)

        for idx, strategy_template in enumerate(self.strategies):
            if self.is_cancelled:
                break
            
            strategy_cmd = strategy_template.replace("{sni}", f'"{sni}"')
            self.progress_changed.emit(idx + 1, total, strategy_cmd)

            parsed_args = shell_split(strategy_cmd)
            cmd_ip, cmd_port = check_ip_and_port_in_cmd(parsed_args)
            
            p_ip = cmd_ip or proxy_ip
            p_port = int(cmd_port or proxy_port)
            
            final_args = []
            if cmd_ip is None:
                final_args.extend(["--ip", p_ip])
            if cmd_port is None:
                final_args.extend(["--port", str(p_port)])
                
            final_args.extend(parsed_args)

            # Ensure port is clean before launch
            ensure_port_available(p_ip, p_port)

            proc = start_byedpi(self.byedpi_path, final_args)
            if not proc:
                err_details = {site: (False, "Ошибка запуска процесса ciadpi") for site in self.sites}
                self.strategy_completed.emit(strategy_template, 0.0, 0, len(self.sites), err_details)
                results.append((strategy_template, 0.0, 0, len(self.sites), err_details))
                continue

            port_ok, port_err = wait_for_proxy_port(proc, p_ip, p_port, timeout=4.0)
            if not port_ok:
                stop_byedpi(proc)
                err_details = {site: (False, port_err) for site in self.sites}
                self.strategy_completed.emit(strategy_template, 0.0, 0, len(self.sites), err_details)
                results.append((strategy_template, 0.0, 0, len(self.sites), err_details))
                wait_for_port_closed(p_ip, p_port, timeout=1.5)
                continue

            if self.is_cancelled:
                stop_byedpi(proc)
                break

            time.sleep(delay)

            success_count = 0
            checked_details = {}
            
            with ThreadPoolExecutor(max_workers=concurrency) as executor:
                futures = {
                    executor.submit(
                        check_url, 
                        p_ip, 
                        p_port, 
                        f"https://{site}", 
                        timeout=timeout
                    ): site
                    for site in self.sites
                }
                
                for future in as_completed(futures):
                    if self.is_cancelled:
                        break
                    site = futures[future]
                    try:
                        success, msg = future.result()
                        checked_details[site] = (success, msg)
                        if success:
                            success_count += 1
                    except Exception as e:
                        checked_details[site] = (False, str(e))

            # PIP PyPI accessibility check
            pypi_domains = ["pypi.org", "files.pythonhosted.org", "pypi.python.org", "pythonhosted.org"]
            pypi_accessible = True
            for domain in pypi_domains:
                if domain in self.sites:
                    if domain not in checked_details or not checked_details[domain][0]:
                        pypi_accessible = False
                        break
                        
            pip_success = False
            pip_msg = "Не проверялось"
            
            if pypi_accessible and not self.is_cancelled:
                import tempfile
                temp_dir = tempfile.mkdtemp()
                try:
                    cmd = [
                        sys.executable, "-m", "pip", "download",
                        "--proxy", f"socks5://127.0.0.1:{p_port}",
                        "--no-cache-dir",
                        "--disable-pip-version-check",
                        "--no-input",
                        "--retries", "1",
                        "--dest", temp_dir,
                        "pytz",
                        "--only-binary=:all:"
                    ]
                    
                    # Detect support for --use-deprecated=legacy-certs (fixes Python 3.14+ / pip 24.2+ SOCKS proxy bug)
                    if not hasattr(self, "_pip_supports_legacy_certs"):
                        try:
                            chk = subprocess.run(
                                [sys.executable, "-m", "pip", "--use-deprecated=legacy-certs", "--version"],
                                stdout=subprocess.DEVNULL,
                                stderr=subprocess.DEVNULL,
                                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
                            )
                            self._pip_supports_legacy_certs = (chk.returncode == 0)
                        except Exception:
                            self._pip_supports_legacy_certs = False
                    
                    if getattr(self, "_pip_supports_legacy_certs", False):
                        cmd.insert(4, "--use-deprecated=legacy-certs")
                    
                    result = subprocess.run(
                        cmd,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        timeout=15.0,
                        creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
                    )
                    
                    if result.returncode == 0:
                        pip_success = True
                        pip_msg = "Успешное скачивание pytz через pip!"
                    else:
                        err_str = result.stderr.decode('utf-8', errors='ignore').strip()
                        meaningful_lines = [
                            l.strip() for l in err_str.splitlines()
                            if l.strip() and not l.strip().startswith("WARNING:") and not l.strip().startswith("Traceback") and not l.strip().startswith("File ")
                        ]
                        summary_err = meaningful_lines[-1] if meaningful_lines else err_str
                        if len(summary_err) > 120:
                            summary_err = summary_err[:120] + "..."
                        pip_msg = f"Ошибка pip: {summary_err}"
                except subprocess.TimeoutExpired:
                    pip_msg = "Таймаут скачивания через pip (15 сек)"
                except Exception as e:
                    pip_msg = f"Ошибка теста pip: {e}"
                finally:
                    try:
                        shutil.rmtree(temp_dir)
                    except:
                        pass
                        
            checked_details["__pip_test__"] = (pip_success, pip_msg)

            stop_byedpi(proc)
            wait_for_port_closed(p_ip, p_port, timeout=2.5)
            time.sleep(0.1)

            if self.is_cancelled:
                break

            pct = (success_count / len(self.sites)) * 100 if self.sites else 0.0
            self.strategy_completed.emit(strategy_template, pct, success_count, len(self.sites), checked_details)
            results.append((strategy_template, pct, success_count, len(self.sites), checked_details))

        self.finished.emit(results)

    def cancel(self):
        self.is_cancelled = True


class ByeDPITesterGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.worker = None
        self.results_data = []
        self.ai_generated_strategies = []
        self.ml_optimizer = ZDPIMLOptimizer() if ZDPIMLOptimizer else None
        self.load_domains()
        self.load_strategies()
        self.load_priority_sites()
        self.init_ui()

    def load_domains(self):
        self.domains = []
        if os.path.exists(SITES_FILE):
            try:
                with open(SITES_FILE, 'r', encoding='utf-8') as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith('#'):
                            self.domains.append(line)
            except Exception as e:
                print(f"Ошибка загрузки доменов: {e}")
        
        if not self.domains:
            self.domains = list(DEFAULT_SITES)
            self.save_domains()

    def save_domains(self):
        try:
            with open(SITES_FILE, 'w', encoding='utf-8') as f:
                f.write("# Список сайтов/доменов для проверки ByeDPI стратегий\n")
                f.write("# Вы можете редактировать этот файл вручную\n\n")
                for domain in self.domains:
                    f.write(f"{domain}\n")
        except Exception as e:
            print(f"Ошибка сохранения доменов: {e}")

    def load_strategies(self):
        self.strategies = []
        if os.path.exists(STRATEGIES_FILE):
            try:
                with open(STRATEGIES_FILE, 'r', encoding='utf-8') as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith('#'):
                            # Strip unsupported Linux-only parameters
                            if os.name == 'nt':
                                tokens = [t for t in line.split() if t not in ('-S', '-Y')]
                                line = ' '.join(tokens)
                            if line:
                                self.strategies.append(line)
            except Exception as e:
                print(f"Ошибка загрузки стратегий: {e}")
        
        if not self.strategies:
            self.strategies = list(DEFAULT_STRATEGIES)
            self.save_strategies()

    def save_strategies(self):
        try:
            with open(STRATEGIES_FILE, 'w', encoding='utf-8') as f:
                f.write("# Список стратегий ByeDPI для тестирования\n")
                f.write("# Вы можете добавлять или удалять стратегии вручную\n\n")
                for strat in self.strategies:
                    f.write(f"{strat}\n")
        except Exception as e:
            print(f"Ошибка сохранения стратегий: {e}")

    def load_priority_sites(self):
        self.priority_sites = []
        if os.path.exists(PRIORITY_SITES_FILE):
            try:
                with open(PRIORITY_SITES_FILE, 'r', encoding='utf-8') as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith('#'):
                            self.priority_sites.append(line)
            except Exception as e:
                print(f"Ошибка загрузки приоритетных сайтов: {e}")
        
        if not self.priority_sites:
            self.priority_sites = [
                s for s in self.domains if 'youtube' in s or 'googlevideo' in s or 'rutracker' in s
            ]
            if not self.priority_sites:
                self.priority_sites = list(self.domains)
            self.save_priority_sites()

    def save_priority_sites(self):
        try:
            with open(PRIORITY_SITES_FILE, 'w', encoding='utf-8') as f:
                f.write("# Список приоритетных сайтов для проверки\n")
                f.write("# Эти сайты отмечены галочками в списке доменов\n\n")
                for site in self.priority_sites:
                    f.write(f"{site}\n")
        except Exception as e:
            print(f"Ошибка сохранения приоритетных сайтов: {e}")

    def init_ui(self):
        self.setWindowTitle(T("Тестер стратегий zDPI (Автономный)", "zDPI Strategies Tester (Standalone)"))
        self.setFixedSize(1080, 730)
        self.setStyleSheet(DARK_STYLESHEET)
        
        main_widget = QWidget()
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(10)
        
        header_layout = QHBoxLayout()
        title_lbl = QLabel("Тестер стратегий zDPI")
        title_lbl.setObjectName("title_lbl")
        header_layout.addWidget(title_lbl)
        main_layout.addLayout(header_layout)
        
        panels_container = QWidget()
        panels_layout = QHBoxLayout()
        panels_layout.setContentsMargins(0, 0, 0, 0)
        panels_layout.setSpacing(15)
        
        # --- LEFT PANEL (Settings & Domains) ---
        left_widget = QWidget()
        left_layout = QVBoxLayout()
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(10)
        
        # 1. Tester Settings Group
        settings_group = QGroupBox("Параметры проверки")
        settings_layout = QVBoxLayout()
        settings_layout.setSpacing(8)
        
        path_layout = QHBoxLayout()
        self.path_edit = QLineEdit(BYEDPI_EXE_DEFAULT)
        self.path_edit.setToolTip("Путь к исполняемому файлу zdpi.exe")
        self.browse_btn = QPushButton("Обзор")
        self.browse_btn.clicked.connect(self.browse_executable)
        path_layout.addWidget(self.path_edit)
        path_layout.addWidget(self.browse_btn)
        settings_layout.addWidget(QLabel("Путь к zdpi.exe:"))
        settings_layout.addLayout(path_layout)
        
        sni_port_layout = QHBoxLayout()
        vbox_sni = QVBoxLayout()
        self.sni_edit = QLineEdit("google.com")
        vbox_sni.addWidget(QLabel("SNI для {sni}:"))
        vbox_sni.addWidget(self.sni_edit)
        
        vbox_port = QVBoxLayout()
        self.port_edit = QLineEdit("1080")
        vbox_port.addWidget(QLabel("Порт SOCKS5:"))
        vbox_port.addWidget(self.port_edit)
        
        sni_port_layout.addLayout(vbox_sni)
        sni_port_layout.addLayout(vbox_port)
        settings_layout.addLayout(sni_port_layout)
        
        num_layout = QHBoxLayout()
        vbox_conc = QVBoxLayout()
        self.conc_spin = QSpinBox()
        self.conc_spin.setRange(1, 50)
        self.conc_spin.setValue(10)
        vbox_conc.addWidget(QLabel("Потоков:"))
        vbox_conc.addWidget(self.conc_spin)
        
        vbox_timeout = QVBoxLayout()
        self.timeout_spin = QDoubleSpinBox()
        self.timeout_spin.setRange(0.5, 30.0)
        self.timeout_spin.setSingleStep(0.5)
        self.timeout_spin.setValue(4.0)
        vbox_timeout.addWidget(QLabel("Таймаут (сек):"))
        vbox_timeout.addWidget(self.timeout_spin)
        
        vbox_delay = QVBoxLayout()
        self.delay_spin = QDoubleSpinBox()
        self.delay_spin.setRange(0.0, 5.0)
        self.delay_spin.setSingleStep(0.1)
        self.delay_spin.setValue(0.2)
        vbox_delay.addWidget(QLabel("Задержка (сек):"))
        vbox_delay.addWidget(self.delay_spin)
        
        num_layout.addLayout(vbox_conc)
        num_layout.addLayout(vbox_timeout)
        num_layout.addLayout(vbox_delay)
        settings_layout.addLayout(num_layout)
        
        settings_group.setLayout(settings_layout)
        left_layout.addWidget(settings_group)
        
        # 2. Domains Manager Group
        domains_group = QGroupBox("Проверяемые домены (отметьте приоритетные)")
        domains_layout = QVBoxLayout()
        domains_layout.setSpacing(8)
        
        self.domains_list = QListWidget()
        self.domains_list.itemChanged.connect(self.on_domain_check_changed)
        self.refresh_domains_list()
        domains_layout.addWidget(self.domains_list)
        
        add_layout = QHBoxLayout()
        self.new_domain_edit = QLineEdit()
        self.new_domain_edit.setPlaceholderText("Добавить новый домен...")
        self.new_domain_edit.returnPressed.connect(self.add_domain)
        self.add_domain_btn = QPushButton(T("Добавить", "Add"))
        self.add_domain_btn.clicked.connect(self.add_domain)
        add_layout.addWidget(self.new_domain_edit)
        add_layout.addWidget(self.add_domain_btn)
        domains_layout.addLayout(add_layout)
        
        btn_row1 = QHBoxLayout()
        self.remove_domain_btn = QPushButton("Удалить выбранный")
        self.remove_domain_btn.clicked.connect(self.remove_domain)
        self.reset_domains_btn = QPushButton("Все (сброс)")
        self.reset_domains_btn.setToolTip("Восстановить полный список по умолчанию")
        self.reset_domains_btn.clicked.connect(self.reset_domains)
        btn_row1.addWidget(self.remove_domain_btn)
        btn_row1.addWidget(self.reset_domains_btn)
        domains_layout.addLayout(btn_row1)

        btn_row2 = QHBoxLayout()
        self.add_yt_btn = QPushButton("+ YouTube & CDN")
        self.add_yt_btn.setToolTip("Добавить домены YouTube и GoogleVideo CDN из ByeByeDPI")
        self.add_yt_btn.clicked.connect(self.preset_add_youtube)
        
        self.only_yt_btn = QPushButton("Только YouTube")
        self.only_yt_btn.setToolTip("Оставить только домены YouTube и GoogleVideo CDN")
        self.only_yt_btn.clicked.connect(self.preset_only_youtube)
        
        btn_row2.addWidget(self.add_yt_btn)
        btn_row2.addWidget(self.only_yt_btn)
        domains_layout.addLayout(btn_row2)
        
        domains_group.setLayout(domains_layout)
        left_layout.addWidget(domains_group)
        
        left_widget.setLayout(left_layout)
        panels_layout.addWidget(left_widget)
        
        # --- RIGHT PANEL (Results & Operations) ---
        right_widget = QWidget()
        right_layout = QVBoxLayout()
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(10)
        
        control_layout = QHBoxLayout()
        self.start_btn = QPushButton("Запустить проверку")
        self.start_btn.setObjectName("start_btn")
        self.start_btn.clicked.connect(self.start_testing)
        
        self.stop_btn = QPushButton(T("Остановить", "Stop"))
        self.stop_btn.setObjectName("stop_btn")
        self.stop_btn.setEnabled(False)
        self.stop_btn.clicked.connect(self.stop_testing)
        
        control_layout.addWidget(self.start_btn)
        control_layout.addWidget(self.stop_btn)
        right_layout.addLayout(control_layout)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        self.progress_bar.setFormat("Готов к тестированию")
        right_layout.addWidget(self.progress_bar)
        
        self.status_desc = QLabel("Нажмите 'Запустить проверку' для старта. В списке %d стратегий." % len(self.strategies))
        self.status_desc.setObjectName("status_desc_lbl")
        right_layout.addWidget(self.status_desc)
        
        # Tabs: Testing Results & AI/ML Optimizer
        self.right_tabs = QTabWidget()
        
        # --- TAB 1: TESTING RESULTS ---
        tab_testing = QWidget()
        tab_test_layout = QVBoxLayout()
        tab_test_layout.setContentsMargins(0, 5, 0, 0)
        tab_test_layout.setSpacing(8)

        table_group = QGroupBox("Таблица результатов (сортировка по клику на заголовок)")
        table_layout = QVBoxLayout()
        table_layout.setContentsMargins(5, 5, 5, 5)
        
        self.results_table = QTableWidget(0, 6)
        self.results_table.setHorizontalHeaderLabels(["#", "Успешность (все)", "Успешность (приор.)", "Успешно", "Тест PIP", "Параметры стратегии"])
        self.results_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.results_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.results_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.results_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.results_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeToContents)
        self.results_table.horizontalHeader().setSectionResizeMode(5, QHeaderView.Stretch)
        self.results_table.itemSelectionChanged.connect(self.strategy_selection_changed)
        self.results_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.results_table.setSelectionMode(QTableWidget.SingleSelection)
        self.results_table.setEditTriggers(QTableWidget.NoEditTriggers)
        
        table_layout.addWidget(self.results_table)
        table_group.setLayout(table_layout)
        table_group.setFixedHeight(270)
        tab_test_layout.addWidget(table_group)
        
        detail_group = QGroupBox("Подробный лог доменов для выбранной стратегии")
        detail_layout = QVBoxLayout()
        detail_layout.setContentsMargins(5, 5, 5, 5)
        
        self.detail_list = QListWidget()
        self.detail_list.setSelectionMode(QListWidget.NoSelection)
        detail_layout.addWidget(self.detail_list)
        detail_group.setLayout(detail_layout)
        detail_group.setFixedHeight(150)
        tab_test_layout.addWidget(detail_group)
        
        actions_layout = QHBoxLayout()
        self.apply_btn = QPushButton("Применить как основную стратегию zDPI")
        self.apply_btn.setObjectName("apply_btn")
        self.apply_btn.setEnabled(False)
        self.apply_btn.clicked.connect(self.apply_selected_strategy)
        
        self.copy_btn = QPushButton("Скопировать команду")
        self.copy_btn.setObjectName("copy_btn")
        self.copy_btn.setEnabled(False)
        self.copy_btn.clicked.connect(self.copy_selected_command)

        self.ai_quick_btn = QPushButton("🧠 Подобрать через ИИ")
        self.ai_quick_btn.clicked.connect(lambda: (self.right_tabs.setCurrentIndex(1), self.on_generate_ai_clicked()))
        
        actions_layout.addWidget(self.apply_btn, stretch=3)
        actions_layout.addWidget(self.copy_btn, stretch=1)
        actions_layout.addWidget(self.ai_quick_btn, stretch=1)
        tab_test_layout.addLayout(actions_layout)

        tab_testing.setLayout(tab_test_layout)
        self.right_tabs.addTab(tab_testing, "📊 Результаты тестов")

        # --- TAB 2: AI / ML OPTIMIZER ---
        tab_ml = QWidget()
        tab_ml_layout = QVBoxLayout()
        tab_ml_layout.setContentsMargins(0, 5, 0, 0)
        tab_ml_layout.setSpacing(8)

        ml_status_group = QGroupBox("Статус модели машинного обучения (AI Strategy Engine)")
        ml_status_layout = QVBoxLayout()
        
        self.ml_status_lbl = QLabel("ИИ готов к обучению. Выполните тестирование или нажмите 'Сгенерировать'.")
        self.ml_factors_lbl = QLabel("Факторы успеха будут рассчитаны после накопления данных тестов.")
        self.ml_factors_lbl.setStyleSheet("color: #a8c3a8; font-style: italic;")
        
        ml_btn_row = QHBoxLayout()
        self.ml_train_btn = QPushButton("🔄 Переобучить модель ИИ")
        self.ml_train_btn.clicked.connect(self.on_retrain_ml_clicked)
        self.ml_generate_btn = QPushButton("🧠 Сгенерировать стратегии с ИИ")
        self.ml_generate_btn.setStyleSheet("background-color: #2b3d39; border-color: #3e5850;")
        self.ml_generate_btn.clicked.connect(self.on_generate_ai_clicked)
        ml_btn_row.addWidget(self.ml_train_btn)
        ml_btn_row.addWidget(self.ml_generate_btn)

        ml_status_layout.addWidget(self.ml_status_lbl)
        ml_status_layout.addWidget(self.ml_factors_lbl)
        ml_status_layout.addLayout(ml_btn_row)
        ml_status_group.setLayout(ml_status_layout)
        tab_ml_layout.addWidget(ml_status_group)

        ai_table_group = QGroupBox("Стратегии, синтезированные искусственным интеллектом")
        ai_table_layout = QVBoxLayout()
        ai_table_layout.setContentsMargins(5, 5, 5, 5)

        self.ai_table = QTableWidget(0, 4)
        self.ai_table.setHorizontalHeaderLabels(["#", "Прогноз успеха", "Стратегия", "Обоснование ИИ"])
        self.ai_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.ai_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.ai_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.ai_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.ai_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.ai_table.setSelectionMode(QTableWidget.SingleSelection)
        self.ai_table.setEditTriggers(QTableWidget.NoEditTriggers)

        ai_table_layout.addWidget(self.ai_table)
        ai_table_group.setLayout(ai_table_layout)
        tab_ml_layout.addWidget(ai_table_group, stretch=3)

        ai_actions_layout = QHBoxLayout()
        self.ai_add_queue_btn = QPushButton("➕ Добавить сгенерированные в очередь тестов")
        self.ai_add_queue_btn.clicked.connect(self.on_add_ai_to_queue_clicked)
        self.ai_apply_btn = QPushButton("💾 Применить выбранную ИИ-стратегию")
        self.ai_apply_btn.setObjectName("apply_btn")
        self.ai_apply_btn.clicked.connect(self.on_apply_ai_selected_clicked)

        ai_actions_layout.addWidget(self.ai_add_queue_btn, stretch=2)
        ai_actions_layout.addWidget(self.ai_apply_btn, stretch=3)
        tab_ml_layout.addLayout(ai_actions_layout)

        tab_ml.setLayout(tab_ml_layout)
        self.right_tabs.addTab(tab_ml, "🧠 ИИ-Оптимизатор")

        right_layout.addWidget(self.right_tabs)
        
        right_widget.setLayout(right_layout)
        panels_layout.addWidget(right_widget)
        
        left_widget.setFixedWidth(340)
        panels_container.setLayout(panels_layout)
        main_layout.addWidget(panels_container)
        
        main_widget.setLayout(main_layout)
        self.setCentralWidget(main_widget)
        
        if not os.path.exists(self.path_edit.text()):
            self.status_desc.setText("Внимание: Файл zdpi.exe (или ciadpi.exe) не найден автоматически. Пожалуйста, укажите путь кнопкой 'Обзор'.")
            self.path_edit.setStyleSheet("border: 1.5px solid #e74c3c;")

        self.update_ml_tab_state()

    def browse_executable(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Выберите исполняемый файл zDPI", "", "Executables (*.exe);;All Files (*)"
        )
        if file_path:
            self.path_edit.setText(os.path.normpath(file_path))
            self.path_edit.setStyleSheet("")
            self.status_desc.setText("Путь к zDPI обновлен.")

    def refresh_domains_list(self):
        self.domains_list.blockSignals(True)
        self.domains_list.clear()
        for domain in self.domains:
            item = QListWidgetItem(domain)
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            if domain in self.priority_sites:
                item.setCheckState(Qt.Checked)
            else:
                item.setCheckState(Qt.Unchecked)
            self.domains_list.addItem(item)
        self.domains_list.blockSignals(False)

    def on_domain_check_changed(self, item):
        domain = item.text()
        if item.checkState() == Qt.Checked:
            if domain not in self.priority_sites:
                self.priority_sites.append(domain)
        else:
            if domain in self.priority_sites:
                self.priority_sites.remove(domain)
        self.save_priority_sites()
        self.recalculate_table_priority_percentages()

    def recalculate_table_priority_percentages(self):
        if not self.results_data:
            return
            
        for row in range(self.results_table.rowCount()):
            strategy = self.results_table.item(row, 5).text()
            for strat, pct, succ, tot, details in self.results_data:
                if strat == strategy:
                    priority_succ = 0
                    priority_tot = 0
                    for site in self.priority_sites:
                        if site in self.domains:
                            priority_tot += 1
                            if site in details and details[site][0]:
                                priority_succ += 1
                                
                    if priority_tot > 0:
                        pri_pct = (priority_succ / priority_tot) * 100
                        text = "%.1f%% (%d/%d)" % (pri_pct, priority_succ, priority_tot)
                    else:
                        text = "-"
                        pri_pct = 0.0
                        
                    item_pri = self.results_table.item(row, 2)
                    if item_pri:
                        item_pri.setText(text)
                        if pri_pct >= 80.0:
                            item_pri.setForeground(QColor("#a8c3a8"))
                        elif pri_pct >= 40.0:
                            item_pri.setForeground(QColor("#c3b5a8"))
                        else:
                            item_pri.setForeground(QColor("#c3a8a8"))
                    break

    def add_domain(self):
        domain = self.new_domain_edit.text().strip().lower()
        if not domain:
            return
        
        if '.' not in domain or len(domain) < 4:
            QMessageBox.warning(self, "Неверный домен", "Пожалуйста, введите корректное доменное имя (например, google.com).")
            return
            
        if domain in self.domains:
            QMessageBox.information(self, "Домен уже есть", "Этот домен уже добавлен в список.")
            return
            
        self.domains.append(domain)
        self.priority_sites.append(domain)
        self.save_domains()
        self.save_priority_sites()
        self.refresh_domains_list()
        self.new_domain_edit.clear()
        self.status_desc.setText("Домен %s добавлен." % domain)
        self.recalculate_table_priority_percentages()

    def remove_domain(self):
        selected_items = self.domains_list.selectedItems()
        if not selected_items:
            QMessageBox.information(self, "Выберите домен", "Пожалуйста, выберите домен из списка для удаления.")
            return
            
        for item in selected_items:
            domain = item.text()
            if domain in self.domains:
                self.domains.remove(domain)
            if domain in self.priority_sites:
                self.priority_sites.remove(domain)
            
        self.save_domains()
        self.save_priority_sites()
        self.refresh_domains_list()
        self.status_desc.setText("Выбранный домен удален.")
        self.recalculate_table_priority_percentages()

    def reset_domains(self):
        reply = QMessageBox.question(
            self, "Сбросить домены", 
            "Восстановить полный список доменов по умолчанию (включая YouTube и CDN)?",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            self.domains = list(DEFAULT_SITES)
            self.priority_sites = [s for s in self.domains if 'youtube' in s or 'googlevideo' in s or 'rutracker' in s]
            self.save_domains()
            self.save_priority_sites()
            self.refresh_domains_list()
            self.status_desc.setText("Список доменов сброшен к полному набору по умолчанию.")
            self.recalculate_table_priority_percentages()

    def preset_add_youtube(self):
        added = 0
        for d in (YOUTUBE_SITES + GOOGLEVIDEO_SITES):
            if d not in self.domains:
                self.domains.append(d)
                self.priority_sites.append(d)
                added += 1
        self.save_domains()
        self.save_priority_sites()
        self.refresh_domains_list()
        self.status_desc.setText("Добавлено %d доменов YouTube и GoogleVideo CDN." % added)
        self.recalculate_table_priority_percentages()
        QMessageBox.information(self, "YouTube пресет", "Добавлено %d новых доменов YouTube/GoogleVideo!" % added)

    def preset_only_youtube(self):
        reply = QMessageBox.question(
            self, "Только YouTube", 
            "Заменить текущий список доменов на эксклюзивный список YouTube & GoogleVideo CDN из ByeByeDPI?",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes
        )
        if reply == QMessageBox.Yes:
            self.domains = list(YOUTUBE_SITES + GOOGLEVIDEO_SITES)
            self.priority_sites = list(self.domains)
            self.save_domains()
            self.save_priority_sites()
            self.refresh_domains_list()
            self.status_desc.setText("Установлен список: Только YouTube & GoogleVideo CDN (%d доменов)." % len(self.domains))
            self.recalculate_table_priority_percentages()

    def start_testing(self):
        byedpi_path = self.path_edit.text().strip()
        if not os.path.exists(byedpi_path):
            QMessageBox.critical(self, T("Ошибка", "Error"), "Исполняемый файл zdpi.exe не найден по указанному пути:\n%s\n\nПожалуйста, нажмите 'Обзор' и укажите zdpi.exe." % byedpi_path)
            return

        if not self.domains:
            QMessageBox.warning(self, "Нет доменов", "Список проверяемых доменов пуст. Добавьте хотя бы один домен.")
            return

        # Force stop running instances to release port
        try:
            from managers import bdsher
            bdsher.stop_byedpi()
            bdsher.get_pip_manager().stop()
        except:
            pass
            
        port_num = 1080
        try:
            port_num = int(self.port_edit.text().strip())
        except ValueError:
            pass
        ensure_port_available('127.0.0.1', port_num)

        self.results_data = []
        self.results_table.setRowCount(0)
        self.detail_list.clear()
        self.progress_bar.setValue(0)
        self.progress_bar.setFormat("Инициализация...")
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.apply_btn.setEnabled(False)
        self.copy_btn.setEnabled(False)
        
        self.path_edit.setEnabled(False)
        self.sni_edit.setEnabled(False)
        self.port_edit.setEnabled(False)
        self.conc_spin.setEnabled(False)
        self.timeout_spin.setEnabled(False)
        self.delay_spin.setEnabled(False)
        self.new_domain_edit.setEnabled(False)
        self.add_domain_btn.setEnabled(False)
        self.remove_domain_btn.setEnabled(False)
        self.reset_domains_btn.setEnabled(False)
        self.add_yt_btn.setEnabled(False)
        self.only_yt_btn.setEnabled(False)

        options = {
            'sni': self.sni_edit.text().strip(),
            'ip': '127.0.0.1',
            'port': str(port_num),
            'concurrency': self.conc_spin.value(),
            'timeout': self.timeout_spin.value(),
            'delay': self.delay_spin.value()
        }

        self.worker = WorkerThread(byedpi_path, self.strategies, self.domains, options)
        self.worker.progress_changed.connect(self.on_progress_changed)
        self.worker.strategy_completed.connect(self.on_strategy_completed)
        self.worker.finished.connect(self.on_testing_finished)
        self.worker.error.connect(self.on_testing_error)
        self.worker.start()

    def stop_testing(self):
        if self.worker and self.worker.isRunning():
            self.progress_bar.setFormat("Остановка...")
            self.worker.cancel()
            self.stop_btn.setEnabled(False)

    def on_progress_changed(self, current, total, strategy_cmd):
        self.progress_bar.setMaximum(total)
        self.progress_bar.setValue(current - 1)
        self.progress_bar.setFormat("Проверка: %d из %d" % (current, total))
        self.status_desc.setText("Активная стратегия: %s" % strategy_cmd)

    def on_strategy_completed(self, strategy, success_rate, success_count, total, details):
        row = self.results_table.rowCount()
        self.results_table.insertRow(row)
        
        # Column 0: Index
        item_idx = QTableWidgetItem(str(row + 1))
        item_idx.setTextAlignment(Qt.AlignCenter)
        self.results_table.setItem(row, 0, item_idx)
        
        # Column 1: Успешность (все)
        item_pct = QTableWidgetItem("%.1f%%" % success_rate)
        item_pct.setTextAlignment(Qt.AlignCenter)
        if success_rate >= 80.0:
            item_pct.setForeground(QColor("#a8c3a8"))
        elif success_rate >= 40.0:
            item_pct.setForeground(QColor("#c3b5a8"))
        else:
            item_pct.setForeground(QColor("#c3a8a8"))
        self.results_table.setItem(row, 1, item_pct)
        
        # Column 2: Успешность (приор.)
        priority_succ = 0
        priority_tot = 0
        for site in self.priority_sites:
            if site in self.domains:
                priority_tot += 1
                if site in details and details[site][0]:
                    priority_succ += 1
                    
        if priority_tot > 0:
            pri_pct = (priority_succ / priority_tot) * 100
            pri_text = "%.1f%% (%d/%d)" % (pri_pct, priority_succ, priority_tot)
        else:
            pri_text = "-"
            pri_pct = 0.0
            
        item_pri = QTableWidgetItem(pri_text)
        item_pri.setTextAlignment(Qt.AlignCenter)
        if pri_pct >= 80.0:
            item_pri.setForeground(QColor("#a8c3a8"))
        elif pri_pct >= 40.0:
            item_pri.setForeground(QColor("#c3b5a8"))
        else:
            item_pri.setForeground(QColor("#c3a8a8"))
        self.results_table.setItem(row, 2, item_pri)
        
        # Column 3: Успешно
        item_succ = QTableWidgetItem("%d / %d" % (success_count, total))
        item_succ.setTextAlignment(Qt.AlignCenter)
        self.results_table.setItem(row, 3, item_succ)
        
        # Column 4: Тест PIP
        pip_res = details.get("__pip_test__", (False, "Не проверялось"))
        pip_ok, pip_msg = pip_res
        item_pip = QTableWidgetItem("OK" if pip_ok else (T("Ошибка", "Error") if T("Ошибка", "Error") in pip_msg or "Таймаут" in pip_msg else "-"))
        item_pip.setTextAlignment(Qt.AlignCenter)
        if pip_ok:
            item_pip.setForeground(QColor("#a8c3a8"))
        else:
            item_pip.setForeground(QColor("#c3a8a8"))
        self.results_table.setItem(row, 4, item_pip)
        
        # Column 5: Параметры стратегии
        item_strat = QTableWidgetItem(strategy)
        self.results_table.setItem(row, 5, item_strat)
        
        self.results_data.append((strategy, success_rate, success_count, total, details))
        self.results_table.scrollToBottom()

        if self.ml_optimizer:
            try:
                self.ml_optimizer.add_result(strategy, success_rate, pri_pct, success_count, total, details)
            except Exception as e:
                print(f"[zDPI ML] Log error: {e}")

    def refresh_results_table(self):
        self.results_table.setRowCount(0)
        for idx, (strategy, success_rate, success_count, total, details) in enumerate(self.results_data):
            row = self.results_table.rowCount()
            self.results_table.insertRow(row)
            
            item_idx = QTableWidgetItem(str(row + 1))
            item_idx.setTextAlignment(Qt.AlignCenter)
            self.results_table.setItem(row, 0, item_idx)
            
            item_pct = QTableWidgetItem("%.1f%%" % success_rate)
            item_pct.setTextAlignment(Qt.AlignCenter)
            if success_rate >= 80.0:
                item_pct.setForeground(QColor("#a8c3a8"))
            elif success_rate >= 40.0:
                item_pct.setForeground(QColor("#c3b5a8"))
            else:
                item_pct.setForeground(QColor("#c3a8a8"))
            self.results_table.setItem(row, 1, item_pct)
            
            priority_succ = 0
            priority_tot = 0
            for site in self.priority_sites:
                if site in self.domains:
                    priority_tot += 1
                    if site in details and details[site][0]:
                        priority_succ += 1
                        
            if priority_tot > 0:
                pri_pct = (priority_succ / priority_tot) * 100
                pri_text = "%.1f%% (%d/%d)" % (pri_pct, priority_succ, priority_tot)
            else:
                pri_text = "-"
                pri_pct = 0.0
                
            item_pri = QTableWidgetItem(pri_text)
            item_pri.setTextAlignment(Qt.AlignCenter)
            if pri_pct >= 80.0:
                item_pri.setForeground(QColor("#a8c3a8"))
            elif pri_pct >= 40.0:
                item_pri.setForeground(QColor("#c3b5a8"))
            else:
                item_pri.setForeground(QColor("#c3a8a8"))
            self.results_table.setItem(row, 2, item_pri)
            
            item_succ = QTableWidgetItem("%d / %d" % (success_count, total))
            item_succ.setTextAlignment(Qt.AlignCenter)
            self.results_table.setItem(row, 3, item_succ)
            
            pip_res = details.get("__pip_test__", (False, "Не проверялось"))
            pip_ok, pip_msg = pip_res
            item_pip = QTableWidgetItem("OK" if pip_ok else (T("Ошибка", "Error") if T("Ошибка", "Error") in pip_msg or "Таймаут" in pip_msg else "-"))
            item_pip.setTextAlignment(Qt.AlignCenter)
            if pip_ok:
                item_pip.setForeground(QColor("#a8c3a8"))
            else:
                item_pip.setForeground(QColor("#c3a8a8"))
            self.results_table.setItem(row, 4, item_pip)
            
            item_strat = QTableWidgetItem(strategy)
            self.results_table.setItem(row, 5, item_strat)

    def on_testing_finished(self, results):
        self.progress_bar.setValue(self.progress_bar.maximum())
        self.progress_bar.setFormat("Проверка завершена!")
        
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.path_edit.setEnabled(True)
        self.sni_edit.setEnabled(True)
        self.port_edit.setEnabled(True)
        self.conc_spin.setEnabled(True)
        self.timeout_spin.setEnabled(True)
        self.delay_spin.setEnabled(True)
        self.new_domain_edit.setEnabled(True)
        self.add_domain_btn.setEnabled(True)
        self.remove_domain_btn.setEnabled(True)
        self.reset_domains_btn.setEnabled(True)
        self.add_yt_btn.setEnabled(True)
        self.only_yt_btn.setEnabled(True)

        if not results:
            self.status_desc.setText("Проверка остановлена или не дала результатов.")
            return

        def get_sort_score(item):
            strat, overall_pct, succ, tot, details = item
            priority_succ = 0
            priority_tot = 0
            for site in self.priority_sites:
                if site in self.domains:
                    priority_tot += 1
                    if site in details and details[site][0]:
                        priority_succ += 1
            pri_pct = (priority_succ / priority_tot * 100) if priority_tot > 0 else 0.0
            return (pri_pct, overall_pct)
            
        self.results_data.sort(key=get_sort_score, reverse=True)
        self.refresh_results_table()

        if not self.results_data:
            self.status_desc.setText("Нет результатов.")
            return
            
        best_strat, overall_pct, succ, tot, details = self.results_data[0]
        
        priority_succ = 0
        priority_tot = 0
        for site in self.priority_sites:
            if site in self.domains:
                priority_tot += 1
                if site in details and details[site][0]:
                    priority_succ += 1
        best_pri_pct = (priority_succ / priority_tot * 100) if priority_tot > 0 else 0.0
                
        if best_pri_pct > 0.0 or overall_pct > 0.0:
            self.status_desc.setText("Лучшая стратегия: %s (Приоритет: %.1f%%, Всего: %.1f%%)" % (
                best_strat, best_pri_pct, overall_pct
            ))
            self.apply_btn.setEnabled(True)
            self.copy_btn.setEnabled(True)
            self.results_table.selectRow(0)
        else:
            self.status_desc.setText("Ни одна из проверенных стратегий не сработала.")
            self.apply_btn.setEnabled(False)
            self.copy_btn.setEnabled(False)

        if self.ml_optimizer:
            try:
                self.ml_optimizer.train_model()
                self.update_ml_tab_state()
            except Exception as e:
                print(f"[zDPI ML] Train error: {e}")

        QMessageBox.information(self, "Проверка завершена", "Тестирование всех стратегий успешно завершено!")

    def update_ml_tab_state(self):
        if not self.ml_optimizer:
            self.ml_status_lbl.setText("Модуль машинного обучения недоступен.")
            return

        cnt = len(self.ml_optimizer.history)
        if cnt == 0:
            self.ml_status_lbl.setText("В истории ML пока нет данных. Запустите тестирование, чтобы обучить модель.")
            self.ml_factors_lbl.setText("ИИ автоматически проанализирует зависимости после завершения тестов.")
        else:
            self.ml_status_lbl.setText(f"Обучено на {cnt} стратегиях в базе опыта. ИИ готов к генерации.")
            if self.ml_optimizer.top_features:
                f_desc = []
                names_map = {
                    "split_pos_midsld": "midsld маркер",
                    "has_quic_drop": "QUIC-Drop (блокировка HTTP/3)",
                    "fake_tmpl_kyber": "Kyber Fake",
                    "fake_tmpl_google": "Google Fake",
                    "fake_ttl": "Оптимальный TTL",
                    "has_tlsrec": "TLS Record split",
                    "split_pos_sniext": "sniext маркер",
                    "has_fake": "Поддельные пакеты (Fake)",
                    "has_disorder": "Disorder перестановка"
                }
                for f_name, imp in self.ml_optimizer.top_features:
                    ru_name = names_map.get(f_name, f_name)
                    f_desc.append(f"{ru_name} ({imp*100:.1f}%)")
                self.ml_factors_lbl.setText("Ключевые факторы успеха по оценке ИИ: " + ", ".join(f_desc))
            else:
                self.ml_factors_lbl.setText("Накапливаются данные для выявления корреляций параметров...")

    def on_retrain_ml_clicked(self):
        if not self.ml_optimizer:
            QMessageBox.warning(self, "Ошибка", "Модуль ML не инициализирован.")
            return
        if len(self.ml_optimizer.history) < 2:
            QMessageBox.information(self, "Мало данных", "Для обучения модели необходимо протестировать хотя бы 2-3 стратегии.")
            return
        ok = self.ml_optimizer.train_model()
        self.update_ml_tab_state()
        if ok:
            QMessageBox.information(self, "Успех", f"Модель ИИ успешно обучена на {len(self.ml_optimizer.history)} тестах!")
        else:
            QMessageBox.warning(self, "Ошибка", "Не удалось обучить модель.")

    def on_generate_ai_clicked(self):
        if not self.ml_optimizer:
            QMessageBox.warning(self, "Ошибка", "Модуль ML недоступен.")
            return
        self.ai_generated_strategies = self.ml_optimizer.generate_ai_strategies(15, self.strategies)
        self.ai_table.setRowCount(0)
        for idx, item in enumerate(self.ai_generated_strategies):
            row = self.ai_table.rowCount()
            self.ai_table.insertRow(row)
            
            i_idx = QTableWidgetItem(str(row + 1))
            i_idx.setTextAlignment(Qt.AlignCenter)
            self.ai_table.setItem(row, 0, i_idx)
            
            score = item["predicted_score"]
            i_score = QTableWidgetItem(f"{score:.1f}%")
            i_score.setTextAlignment(Qt.AlignCenter)
            if score >= 80.0:
                i_score.setForeground(QColor("#a8c3a8"))
            elif score >= 50.0:
                i_score.setForeground(QColor("#c3b5a8"))
            else:
                i_score.setForeground(QColor("#c3a8a8"))
            self.ai_table.setItem(row, 1, i_score)
            
            i_strat = QTableWidgetItem(item["strategy"])
            self.ai_table.setItem(row, 2, i_strat)
            
            i_reason = QTableWidgetItem(item.get("reason", ""))
            i_reason.setForeground(QColor("#a0c0a0"))
            self.ai_table.setItem(row, 3, i_reason)
            
        if self.ai_generated_strategies:
            self.ai_table.selectRow(0)
            self.status_desc.setText(f"ИИ сгенерировал {len(self.ai_generated_strategies)} оптимизированных стратегий.")
        else:
            self.status_desc.setText("ИИ не нашел новых стратегий. Запустите тесты для расширения опыта.")

    def on_add_ai_to_queue_clicked(self):
        if not self.ai_generated_strategies:
            QMessageBox.information(self, "Нет стратегий", "Сначала нажмите 'Сгенерировать стратегии с ИИ'.")
            return
        added = 0
        for item in self.ai_generated_strategies:
            strat = item["strategy"]
            if strat not in self.strategies:
                self.strategies.append(strat)
                added += 1
        self.save_strategies()
        self.status_desc.setText(f"Добавлено {added} ИИ-стратегий в очередь тестирования (всего: {len(self.strategies)}).")
        QMessageBox.information(self, "Добавлено", f"Успешно добавлено {added} новых стратегий от ИИ в список тестирования!\nТеперь вы можете запустить проверку.")
        self.right_tabs.setCurrentIndex(0)

    def on_apply_ai_selected_clicked(self):
        selected = self.ai_table.selectedRanges()
        if not selected:
            QMessageBox.warning(self, "Выберите стратегию", "Пожалуйста, выберите строку в таблице сгенерированных стратегий.")
            return
        row = selected[0].topRow()
        if row >= len(self.ai_generated_strategies):
            return
        strat = self.ai_generated_strategies[row]["strategy"]
        
        sni = self.sni_edit.text().strip()
        final_params = strat.replace("{sni}", sni)
        if not any(arg in final_params.split() for arg in ['-p', '--port']) and not any(arg.startswith('-p') and len(arg) > 2 and arg[2].isdigit() for arg in final_params.split()):
            final_params = "-p 1780 " + final_params
            
        exe_path = self.path_edit.text().strip()
        full_cmd = f'"{exe_path}" {final_params}'
        QApplication.clipboard().setText(full_cmd)
        
        saved = False
        try:
            config = None
            if config_manager:
                config = config_manager.load_config()
            else:
                for c_path in [
                    os.path.join(SCRIPT_DIR, "data", "config.json"),
                    os.path.join(SCRIPT_DIR, "config.json"),
                    os.path.join(os.path.dirname(SCRIPT_DIR), "data", "config.json"),
                    os.path.join(os.path.dirname(SCRIPT_DIR), "config.json")
                ]:
                    if os.path.exists(c_path):
                        with open(c_path, 'r', encoding='utf-8') as f:
                            config = json.load(f)
                            break
            if config is not None:
                config["use_custom_settings"] = True
                config["byedpi_params"] = final_params
                if config_manager:
                    config_manager.save_config(config)
                saved = True
                try:
                    from managers import bdsher
                    mgr = bdsher.get_manager(config)
                    mgr.update_config(config)
                except Exception:
                    pass
        except Exception as e:
            print(f"Config save error: {e}")
            
        msg = f"ИИ-стратегия успешно применена!\n\nПараметры:\n{final_params}\n\n"
        if saved:
            msg += "Параметры сохранены в конфигурацию ToInet-MAX."
        else:
            msg += "Команда запуска скопирована в буфер обмена."
        QMessageBox.information(self, "ИИ-стратегия применена", msg)

    def on_testing_error(self, err_msg):
        QMessageBox.critical(self, T("Ошибка", "Error"), "Произошла ошибка при тестировании:\n%s" % err_msg)
        self.on_testing_finished([])

    def strategy_selection_changed(self):
        selected_ranges = self.results_table.selectedRanges()
        if not selected_ranges:
            self.detail_list.clear()
            self.apply_btn.setEnabled(False)
            self.copy_btn.setEnabled(False)
            return

        row = selected_ranges[0].topRow()
        if row >= len(self.results_data):
            return
            
        strategy, pct, succ, tot, details = self.results_data[row]
        self.detail_list.clear()
        
        for site, (success, msg) in details.items():
            prefix = "OK" if success else "ERR"
            item_text = "[%s]  %s   :   %s" % (prefix, site, msg)
            self.detail_list.addItem(item_text)
            
            list_item = self.detail_list.item(self.detail_list.count() - 1)
            if success:
                list_item.setForeground(QColor("#a8c3a8"))
            else:
                list_item.setForeground(QColor("#c3a8a8"))
                
        self.apply_btn.setEnabled(True)
        self.copy_btn.setEnabled(True)

    def get_selected_cmd(self):
        selected_ranges = self.results_table.selectedRanges()
        if not selected_ranges:
            return None, None
        row = selected_ranges[0].topRow()
        if row >= len(self.results_data):
            return None, None
        strategy, pct, succ, tot, details = self.results_data[row]
        
        sni = self.sni_edit.text().strip()
        final_params = strategy.replace("{sni}", sni)
        
        params_list = final_params.split()
        has_port = False
        for arg in params_list:
            if arg == '-p' or arg == '--port':
                has_port = True
                break
            elif arg.startswith('-p') and len(arg) > 2 and arg[2].isdigit():
                has_port = True
                break
        if not has_port:
            final_params = f"-p {self.port_edit.text().strip()} " + final_params
                
        return strategy, final_params

    def copy_selected_command(self):
        strategy, final_params = self.get_selected_cmd()
        if not final_params:
            return
            
        exe_path = self.path_edit.text().strip()
        full_command = f'"{exe_path}" {final_params}'
        
        clipboard = QApplication.clipboard()
        clipboard.setText(full_command)
        
        self.status_desc.setText("Команда запуска скопирована в буфер обмена!")
        QMessageBox.information(
            self, "Команда скопирована", 
            "Готовая команда запуска ByeDPI скопирована в буфер обмена:\n\n%s" % full_command
        )

    def apply_selected_strategy(self):
        selected_ranges = self.results_table.selectedRanges()
        if not selected_ranges:
            QMessageBox.warning(self, "Выберите стратегию", "Пожалуйста, выберите стратегию из таблицы результатов для применения.")
            return

        row = selected_ranges[0].topRow()
        if row >= len(self.results_data):
            return
            
        strategy, pct, succ, tot, details = self.results_data[row]
        sni = self.sni_edit.text().strip()
        final_params = strategy.replace("{sni}", sni)
        
        params_list = final_params.split()
        has_port = False
        for arg in params_list:
            if arg == '-p' or arg == '--port':
                has_port = True
                break
            elif arg.startswith('-p') and len(arg) > 2 and arg[2].isdigit():
                has_port = True
                break
        if not has_port:
            final_params = "-p 1780 " + final_params
            
        exe_path = self.path_edit.text().strip()
        full_cmd = f'"{exe_path}" {final_params}'
        QApplication.clipboard().setText(full_cmd)

        saved_to_project = False
        try:
            config = None
            if config_manager:
                config = config_manager.load_config()
            else:
                config_candidates = [
                    os.path.join(SCRIPT_DIR, "data", "config.json"),
                    os.path.join(SCRIPT_DIR, "config.json"),
                    os.path.join(os.path.dirname(SCRIPT_DIR), "data", "config.json"),
                    os.path.join(os.path.dirname(SCRIPT_DIR), "config.json")
                ]
                for c_path in config_candidates:
                    if os.path.exists(c_path):
                        with open(c_path, 'r', encoding='utf-8') as f:
                            config = json.load(f)
                            config_target_path = c_path
                            break

            if config is not None:
                config["use_custom_settings"] = True
                config["byedpi_params"] = final_params
                
                if config_manager:
                    config_manager.save_config(config)
                else:
                    with open(config_target_path, 'w', encoding='utf-8') as f:
                        json.dump(config, f, ensure_ascii=False, indent=2)
                saved_to_project = True

                try:
                    from managers import bdsher
                    mgr = bdsher.get_manager(config)
                    mgr.update_config(config)
                except Exception:
                    pass
        except Exception as e:
            print(f"Non-fatal config save notification: {e}")

        msg = "Стратегия выбрана и скопирована в буфер обмена!\n\n"
        msg += f"Команда запуска:\n{full_cmd}\n\n"
        if saved_to_project:
            msg += "Также параметры сохранены в конфигурационный файл ToInet-MAX."
        else:
            msg += "Вы можете вставить эту команду в командную строку или ярлык запуска zdpi."
            
        QMessageBox.information(self, "Стратегия применена", msg)


def main():
    app = QApplication(sys.argv)
    window = ByeDPITesterGUI()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
