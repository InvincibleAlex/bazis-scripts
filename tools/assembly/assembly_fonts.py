"""Resolve a body font independently of the Windows drive or user profile."""
import os
from pathlib import Path
from reportlab import __file__ as reportlab_file
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

def register_body_font():
    candidates=[Path(os.environ.get('WINDIR','C:/Windows'))/'Fonts'/'arial.ttf',Path(reportlab_file).parent/'fonts'/'Vera.ttf']
    for candidate in candidates:
        if candidate.is_file():pdfmetrics.registerFont(TTFont('Body',str(candidate)));return str(candidate)
    raise FileNotFoundError('Lipsește fontul Arial din Windows și fontul de rezervă din pachetul ReportLab')
