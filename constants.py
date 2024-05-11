from pathlib import Path

__all__ = ['PHOTOS_DIR', 'DATA_DIR']

BASE_DIR = Path(__file__).parent

PHOTOS_DIR = BASE_DIR / 'photos'
DATA_DIR = BASE_DIR / 'check-lists'
