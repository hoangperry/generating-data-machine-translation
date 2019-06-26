import glob
import concurrent.futures
import traceback
import os
from pdfminer.pdfinterp import PDFResourceManager, PDFPageInterpreter
from pdfminer.converter import TextConverter
from pdfminer.layout import LAParams
from pdfminer.pdfpage import PDFPage
from io import StringIO
from utils import chunks, ensure_dir


def convert_pdf_to_txt(path):
    rsrcmgr = PDFResourceManager()
    retstr = StringIO()
    codec = 'utf-8'
    laparams = LAParams()
    device = TextConverter(rsrcmgr, retstr, codec=codec, laparams=laparams)
    fp = open(path, 'rb')
    interpreter = PDFPageInterpreter(rsrcmgr, device)
    password = ""
    maxpages = 0
    caching = True
    pagenos=set()
    ret = []
    for page_number, page in enumerate(PDFPage.get_pages(fp, pagenos, maxpages=maxpages,
    								password=password, caching=caching, check_extractable=True)):

        interpreter.process_page(page)
        ret.append(retstr.getvalue())
        retstr.truncate(0)
        retstr.seek(0)
        print("\rprocess " + str(page_number) + " pages from " + str(path), end="")

    fp.close()
    device.close()
    retstr.close()
    return ret


def save_mapped_text(pages_text, path_file):
	dir_save = path_file.replace('.pdf', '/')
	print(dir_save)
	ensure_dir(dir_save)
	for idx, page in enumerate(pages_text):
		page_file = open(dir_save + 'page_' + str(idx) + '.txt', mode="w", encoding="utf-8")
		page_file.write(page)
		page_file.close()


def run_extract(list_path_file):
	for path in list_path_file:
		dict_pages = convert_pdf_to_txt(path)
		save_mapped_text(dict_pages, path)

