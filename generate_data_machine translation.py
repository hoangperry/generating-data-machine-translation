import glob
import pytesseract 
import random
import time
import multiprocessing
import concurrent.futures
from docx import Document, shared, enum

thread_count = multiprocessing.cpu_count() - 1
source_path = "source_file/test.txt"


def chunks(l, n):
    """Yield successive n-sized chunks from l."""
    ret = []
    for i in range(0, len(l), n):
        ret.append(l[i:i+n])
    return ret


def create_docx_file(source_path, batch_size=100, max_word_per_line=12, min_word_per_line = 4):
    font_name = 'Times New Roman'
    font_size = shared.Pt(13)
    file_reader = open(source_path, 'r', encoding='utf-8')
    start_time = time.time()
    lines = file_reader.readlines()
    input_thread = chunks(lines, int(len(lines)/thread_count))
    id_threads = range(thread_count)

    # with concurrent.futures.ProcessPoolExecutor(max_workers=thread) as executor:
    #     executor.map(write_docx, input_thread, id_threads)


def main():
    create_docx_file(source_path)

if __name__ == "__main__":
    main()