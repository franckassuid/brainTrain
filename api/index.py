#!/usr/bin/env python3
"""
Point d'entrée Serverless Vercel pour BrainTrain API.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Inclusion de la racine et du dossier files/ dans le sys.path
ROOT_DIR = Path(__file__).resolve().parent.parent
FILES_DIR = ROOT_DIR / "files"
sys.path.insert(0, str(ROOT_DIR))
sys.path.insert(0, str(FILES_DIR))

from server import BrainTrainHandler


class handler(BrainTrainHandler):
    """Handler compatible avec le runtime Python de Vercel (@vercel/python)."""
    pass
