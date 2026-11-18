#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
zDPI Machine Learning Strategy Optimizer
========================================
Intelligent ML engine for predicting, evaluating, and synthesizing 
anti-DPI circumvention strategies based on historical test data.

Uses scikit-learn (RandomForest / GradientBoosting) with feature extraction
and genetic / Bayesian strategy synthesis.
"""

import os
import sys
import re
import json
import time
import random
from typing import List, Dict, Tuple, Any, Optional

# Optional ML backend:
# By default, to prevent bundling massive deep learning / scientific packages
# (torch, scipy, numpy, transformers ~2.5+ GB) into the distribution, we use a
# built-in lightweight pure-Python ML optimizer (KNN surrogate predictor,
# feature correlation analysis, and genetic mutation/synthesis).
# Full scikit-learn model training can be enabled optionally in non-frozen environments
# via the TOINET_ENABLE_SKLEARN=1 environment variable.
HAS_SKLEARN = False
RandomForestRegressor = None

FEATURE_NAMES = [
    "has_fake",
    "fake_ttl",
    "fake_tmpl_google",
    "fake_tmpl_kyber",
    "fake_tmpl_rutracker",
    "fake_tmpl_other",
    "has_split",
    "split_pos_midsld",
    "split_pos_sniext",
    "split_pos_sld",
    "split_pos_sni",
    "split_pos_num",
    "has_disorder",
    "disorder_pos_midsld",
    "disorder_pos_num",
    "has_tlsrec",
    "tlsrec_pos_midsld",
    "tlsrec_pos_sniext",
    "has_multisplit",
    "has_oob",
    "has_quic_drop",
    "has_fake_sni",
    "has_http_mods",
    "has_auto_detect",
    "num_stages"
]


def extract_features(strategy_str: str) -> List[float]:
    """
    Extract a normalized numerical feature vector from a ByeDPI / Zapret / zDPI strategy string.
    """
    s = strategy_str.strip().lower()
    feat = {name: 0.0 for name in FEATURE_NAMES}

    # 1. Fake
    if "--dpi-desync" in s and "fake" in s:
        feat["has_fake"] = 1.0
    elif any(f in s for f in ["-f", "--fake"]):
        feat["has_fake"] = 1.0

    # Fake TTL
    ttl_match = re.search(r'(?:--dpi-desync-ttl|--ttl|-t)\s*=?\s*(\d+)', s)
    if ttl_match:
        feat["fake_ttl"] = float(ttl_match.group(1))
    elif feat["has_fake"] > 0:
        feat["fake_ttl"] = 3.0

    # Fake templates
    if "google" in s:
        feat["fake_tmpl_google"] = 1.0
    if "kyber" in s:
        feat["fake_tmpl_kyber"] = 1.0
    if "rutracker" in s:
        feat["fake_tmpl_rutracker"] = 1.0
    if any(k in s for k in ["-f-", "--fake -", "fake-data", "0x"]):
        feat["fake_tmpl_other"] = 1.0

    # 2. Split
    if "split" in s or "-s" in s:
        feat["has_split"] = 1.0

    # Split positions
    if "midsld" in s:
        feat["split_pos_midsld"] = 1.0
    if "sniext" in s:
        feat["split_pos_sniext"] = 1.0
    if "endsld" in s or re.search(r'\bsld\b', s):
        feat["split_pos_sld"] = 1.0
    if re.search(r'\bsni\b', s) or "+s" in s:
        feat["split_pos_sni"] = 1.0

    num_split = re.search(r'(?:split-pos|split|-s)\s*=?\s*(\d+)', s)
    if num_split:
        feat["split_pos_num"] = float(num_split.group(1))

    # 3. Disorder
    if "disorder" in s or "-d" in s:
        feat["has_disorder"] = 1.0
        if "midsld" in s:
            feat["disorder_pos_midsld"] = 1.0
        d_num = re.search(r'(?:-d|disorder)\s*=?\s*(\d+)', s)
        if d_num:
            feat["disorder_pos_num"] = float(d_num.group(1))

    # 4. TLS Record
    if "tlsrec" in s or "-r" in s:
        feat["has_tlsrec"] = 1.0
        if "midsld" in s:
            feat["tlsrec_pos_midsld"] = 1.0
        if "sniext" in s:
            feat["tlsrec_pos_sniext"] = 1.0

    # 5. Multisplit
    if "multisplit" in s or s.count("-s") > 1 or "," in (re.search(r'split-pos\s*=?\s*([^\s]+)', s).group(1) if "split-pos" in s else ""):
        feat["has_multisplit"] = 1.0

    # 6. OOB
    if "oob" in s or "-o" in s:
        feat["has_oob"] = 1.0

    # 7. QUIC drop
    if any(q in s for q in ["--quic-drop", "--drop-quic", "-q 1", "-qr"]):
        feat["has_quic_drop"] = 1.0

    # 8. Fake SNI
    if any(n in s for n in ["--dpi-desync-fake-sni", "--fake-sni", "-n "]):
        feat["has_fake_sni"] = 1.0

    # 9. HTTP mods
    if any(m in s for m in ["-m", "--mod-http"]):
        feat["has_http_mods"] = 1.0

    # 10. Auto detect
    if any(a in s for a in ["-a", "--auto"]):
        feat["has_auto_detect"] = 1.0

    # Stages count
    stages = len(re.findall(r'-(?:s|d|f|r|o|q)\b|--dpi-desync\b', s))
    feat["num_stages"] = float(max(1, stages))

    return [feat[name] for name in FEATURE_NAMES]


class ZDPIMLOptimizer:
    """
    ML Optimizer that trains on test outcomes and generates new anti-DPI strategies.
    """
    def __init__(self, history_file: Optional[str] = None):
        if history_file is None:
            try:
                from managers.system_utils import get_base_dir
                base_dir = get_base_dir()
            except Exception:
                base_dir = os.path.dirname(os.path.abspath(__file__))
            self.history_file = os.path.join(base_dir, "zdpi_ml_history.json")
        else:
            self.history_file = history_file

        self.history: List[Dict[str, Any]] = []
        self.model = None
        self.r2_score = 0.0
        self.top_features: List[Tuple[str, float]] = []
        self.load_history()
        self.train_model()

    def load_history(self) -> None:
        if os.path.exists(self.history_file):
            try:
                with open(self.history_file, 'r', encoding='utf-8') as f:
                    self.history = json.load(f)
            except Exception as e:
                print(f"[zDPI ML] Ошибка загрузки истории: {e}")
                self.history = []

    def save_history(self) -> None:
        try:
            with open(self.history_file, 'w', encoding='utf-8') as f:
                json.dump(self.history, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"[zDPI ML] Ошибка сохранения истории: {e}")

    def add_result(self, strategy: str, overall_pct: float, priority_pct: float, 
                   success_count: int, total_sites: int, details: Optional[Dict] = None) -> None:
        """
        Record a tested strategy and update ML experience.
        """
        strategy = strategy.strip()
        if not strategy:
            return

        # Score calculation: 70% weight on priority domains (YouTube, CDN), 30% overall
        score = (0.7 * priority_pct) + (0.3 * overall_pct)

        # Check for existing record
        for item in self.history:
            if item.get("strategy") == strategy:
                item["overall_pct"] = overall_pct
                item["priority_pct"] = priority_pct
                item["score"] = score
                item["success_count"] = success_count
                item["total_sites"] = total_sites
                item["timestamp"] = time.time()
                self.save_history()
                return

        entry = {
            "strategy": strategy,
            "overall_pct": round(overall_pct, 2),
            "priority_pct": round(priority_pct, 2),
            "score": round(score, 2),
            "success_count": success_count,
            "total_sites": total_sites,
            "timestamp": time.time(),
            "features": extract_features(strategy)
        }
        self.history.append(entry)
        self.save_history()

    def train_model(self) -> bool:
        """
        Train ML regressor on historical test data.
        """
        if len(self.history) < 2:
            return False

        X = [item["features"] for item in self.history]
        y = [item["score"] for item in self.history]

        # Optional scikit-learn backend (if explicitly enabled and installed)
        if os.environ.get("TOINET_ENABLE_SKLEARN", "0") == "1":
            try:
                import importlib
                sklearn_ensemble = importlib.import_module("sklearn.ensemble")
                rf_cls = getattr(sklearn_ensemble, "RandomForestRegressor")
                self.model = rf_cls(n_estimators=40, max_depth=6, random_state=42)
                self.model.fit(X, y)
                importances = self.model.feature_importances_
                paired = list(zip(FEATURE_NAMES, importances))
                paired.sort(key=lambda p: p[1], reverse=True)
                self.top_features = [(name, float(val)) for name, val in paired if val > 0.03][:5]
                return True
            except Exception as e:
                print(f"[zDPI ML] Ошибка обучения sklearn модели, переход на встроенный движок: {e}")

        # Lightweight pure-Python surrogate model (KNN + correlation analysis)
        self.model = "fallback_knn"

        # Calculate pure-Python feature importance based on correlation with score
        try:
            n = len(y)
            avg_y = sum(y) / n
            var_y = sum((val - avg_y) ** 2 for val in y)
            if var_y > 1e-9:
                correlations = []
                for j, fname in enumerate(FEATURE_NAMES):
                    col = [row[j] for row in X]
                    avg_c = sum(col) / n
                    var_c = sum((c - avg_c) ** 2 for c in col)
                    if var_c > 1e-9:
                        cov = sum((c - avg_c) * (val - avg_y) for c, val in zip(col, y))
                        r = max(0.0, cov / ((var_c * var_y) ** 0.5))
                        correlations.append((fname, r))
                    else:
                        correlations.append((fname, 0.0))
                total_r = sum(c[1] for c in correlations)
                if total_r > 0:
                    paired = [(fname, r / total_r) for fname, r in correlations]
                    paired.sort(key=lambda p: p[1], reverse=True)
                    self.top_features = [(name, float(val)) for name, val in paired if val > 0.03][:5]
                else:
                    self.top_features = []
            else:
                self.top_features = []
        except Exception as e:
            print(f"[zDPI ML] Ошибка анализа факторов: {e}")
            self.top_features = []

        return True

    def predict_score(self, strategy: str) -> float:
        """
        Predict circumvention success score (0.0 to 100.0) for an untested strategy.
        """
        feat = extract_features(strategy)
        if self.model and self.model != "fallback_knn":
            try:
                val = self.model.predict([feat])[0]
                return float(max(0.0, min(100.0, val)))
            except Exception:
                pass

        # Lightweight pure-Python heuristic prediction using weighted history comparison (KNN)
        if not self.history:
            return 50.0

        scores = []
        weights = []
        for item in self.history:
            h_feat = item.get("features", extract_features(item["strategy"]))
            # Euclidean distance in feature space
            dist = sum((a - b) ** 2 for a, b in zip(feat, h_feat)) ** 0.5
            weight = 1.0 / (1.0 + dist)
            scores.append(item["score"])
            weights.append(weight)

        total_w = sum(weights)
        if total_w > 0:
            pred = sum(s * w for s, w in zip(scores, weights)) / total_w
            return float(max(0.0, min(100.0, pred)))
        return 50.0

    def generate_ai_strategies(self, count: int = 10, existing_list: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """
        Synthesize new, high-potential strategies using Genetic Mutation & ML Ranking.
        """
        existing = set(existing_list or [])
        for item in self.history:
            existing.add(item["strategy"])

        # Top candidate components learned from DPI bypass studies
        modes = [
            "fake,split2",
            "fake,disorder2",
            "fake,multisplit",
            "fakedsplit",
            "fake,tlsrec",
            "tlsrec",
            "fakeddisorder"
        ]
        positions = ["midsld", "sniext", "sld", "sni", "1", "2", "3", "1,midsld", "1,sniext,midsld"]
        fakes = ["google", "kyber", "rutracker"]
        ttls = [2, 3, 4, 5, 8]
        quic_opts = ["--quic-drop", ""]

        candidates = set()

        # 1. Recombine from top-performing historical strategies
        sorted_history = sorted(self.history, key=lambda x: x["score"], reverse=True)
        top_history = sorted_history[:5]

        for item in top_history:
            strat = item["strategy"]
            # Mutation: alter TTL
            for new_ttl in [2, 3, 4, 5]:
                mutated = re.sub(r'--dpi-desync-ttl=\d+', f'--dpi-desync-ttl={new_ttl}', strat)
                mutated = re.sub(r'-t\s*\d+', f'-t {new_ttl}', mutated)
                candidates.add(mutated)
            # Mutation: swap fake template
            for new_tmpl in fakes:
                mutated = re.sub(r'--dpi-desync-fake-tls=\w+', f'--dpi-desync-fake-tls={new_tmpl}', strat)
                candidates.add(mutated)
            # Mutation: add / swap midsld
            if "midsld" not in strat:
                if "--dpi-desync-split-pos=" in strat:
                    mutated = re.sub(r'--dpi-desync-split-pos=[^\s]+', '--dpi-desync-split-pos=midsld', strat)
                    candidates.add(mutated)
            # Mutation: ensure quic-drop
            if "--quic-drop" not in strat:
                candidates.add(strat + " --quic-drop")

        # 2. Parametric synthesis of Zapret & ByeDPI strategies
        for m in modes:
            for p in positions:
                for f in fakes:
                    for t in ttls:
                        for q in quic_opts:
                            q_str = f" {q}" if q else ""
                            cmd = f"--dpi-desync={m} --dpi-desync-split-pos={p} --dpi-desync-fake-tls={f} --dpi-desync-ttl={t}{q_str}"
                            candidates.add(cmd.strip())

        # 3. ByeDPI-style syntax combinations
        for p in ["midsld", "sniext", "1+s", "2+s", "3+s"]:
            for t in [3, 4, 5]:
                for q in ["--quic-drop", ""]:
                    q_str = f" {q}" if q else ""
                    candidates.add(f"-s {p} -f {p} -r {p} -t {t}{q_str}".strip())
                    candidates.add(f"-d {p} -f 1 -t {t}{q_str}".strip())
                    candidates.add(f"-s 1 -d {p} -f -1 -t {t}{q_str}".strip())

        # Filter out already tested or existing
        novel_candidates = [c for c in candidates if c not in existing]

        # Score all novel candidates using ML
        scored = []
        for cand in novel_candidates:
            pred_score = self.predict_score(cand)
            scored.append({
                "strategy": cand,
                "predicted_score": round(pred_score, 1),
                "features": extract_features(cand),
                "reason": self._explain_recommendation(cand)
            })

        scored.sort(key=lambda x: x["predicted_score"], reverse=True)
        return scored[:count]

    def _explain_recommendation(self, strategy: str) -> str:
        """
        Human-readable explanation of why this strategy was prioritized by AI.
        """
        reasons = []
        if "midsld" in strategy:
            reasons.append("Маркер midsld (обход SNI-фильтров)")
        if "kyber" in strategy:
            reasons.append("Kyber Fake (проходит DPI ТСПУ)")
        elif "google" in strategy:
            reasons.append("Google Fake (высокая совместимость)")
        if "--quic-drop" in strategy:
            reasons.append("QUIC-Drop (ускорение YouTube 4K)")
        if re.search(r'ttl=[234]|t [234]', strategy):
            reasons.append("Оптимальный TTL (2-4)")
        if "tlsrec" in strategy:
            reasons.append("TLS-Record расщепление")
        if not reasons:
            reasons.append("Комбинация параметров с высоким рейтингом")
        return ", ".join(reasons)
