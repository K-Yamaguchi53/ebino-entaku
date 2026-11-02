"""Silence pdfminer's font warnings ("Could not get FontBBox ...").

Real slides print thousands of them, which buries the counts the teacher reads.
Errors still show.
"""

import logging
import warnings

PDF_LOGGERS = ("pdfminer", "pdfplumber")


def quiet_pdf_warnings() -> None:
    for name in PDF_LOGGERS:
        logging.getLogger(name).setLevel(logging.ERROR)
    warnings.filterwarnings("ignore", message=r".*FontBBox.*")
