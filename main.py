import glob
import pytesseract 
import random
import time
import multiprocessing
import concurrent.futures
import platform
import os
import shutil
import subprocess
from PIL import Image
from docx import Document, shared, enum
from pdfminer.pdfinterp import PDFResourceManager, PDFPageInterpreter
from pdfminer.converter import TextConverter
from pdfminer.layout import LAParams
from pdfminer.pdfpage import PDFPage
from io import StringIO
from utils import chunks, ensure_dir
from docx_gen import write_docx
from extract_pdf import run_extract
from pdf2image import convert_from_path
from augmentation_image import MultiThreadGenerator as NoiseGenerator


if platform.system() == "Windows":
    import win32com.client as client
elif platform.system() == "Linux":
    cline = None


source_path = "example/test.txt"


outdir_docx = "temp_docx/"
outdir_pdf = "temp_pdf/"
outdir_image = "image_out/"
outdir_noise_image = "noised_image/"
pred_dir = "pred_txt/"
gt_dir = "ground_truth_txt/"
ocred_dir = "ocr-ed/"
deleted_dir = "deleted_files/"
final_out = "final_output/"
thread_count = multiprocessing.cpu_count() - 1


def create_docx_file(source_path, outdir):
    # function to run write_docx with multihtread
    file_reader = open(source_path, 'r', encoding='utf-8')
    start_time = time.time()
    lines = file_reader.readlines()
    input_thread = chunks(lines, int(len(lines)/thread_count))
    id_threads = range(thread_count)
    outdirs = [outdir] * thread_count
    with concurrent.futures.ProcessPoolExecutor(max_workers=thread_count) as executor:
        executor.map(write_docx, input_thread, id_threads, outdirs)
    file_reader.close()


def convert_docx_to_pdf(inputdir, outdir):
    if client == None:
        """
        convert a doc/docx document to pdf format (linux only, requires libreoffice)
        :param doc: path to document
        """
        count = 0
        for in_file in glob.glob(inputdir + "*.docx"):
            start_time = time.time()
            args = [
                "libreoffice",
                '--headless',
                '--convert-to',
                'pdf',
                '--outdir',
                outdir,
                in_file
            ]
            process = subprocess.run(args,
                                    stdout=subprocess.PIPE,
                                    stderr=subprocess.PIPE)            
            count += 1
            print("\rProcessed: " + str(count) + " || time: " + str(time.time() - start_time), end="")

    else:
        wdFormatPDF = 17
        word = client.Dispatch('Word.Application')
        count = 0
        ensure_dir(outdir)
        for in_file in glob.glob(inputdir + "*.docx"):
            start_time = time.time()
            in_file = os.path.join(os.getcwd(), in_file)
            outdir = os.path.join(os.getcwd(), outdir)
            out_file = os.path.join(outdir, os.path.basename(in_file).replace(".docx", ".pdf"))
            doc = word.Documents.Open(in_file)
            doc.SaveAs(out_file, FileFormat=wdFormatPDF)
            count += 1
            print("\rProcessed: " + str(count) + " || time: " + str(time.time() - start_time), end="")
            doc.Close()
        word.Quit()


def extract_text_from_pdf(inputdir):
	list_path_file = glob.glob(inputdir + "*.pdf")
	chunks_path_file = chunks(list_path_file, int(len(list_path_file)/thread_count))
	with concurrent.futures.ProcessPoolExecutor(max_workers=thread_count) as executor:
		executor.map(run_extract, chunks_path_file)


def extract_image_from_pdf(inputdir, outdir):
    for file_name in glob.glob(inputdir + "*.pdf"):
        pages = convert_from_path(file_name, thread_count=int(thread_count/2))
        
        print("\rProcessing file: " + str(file_name), end="\t")
        folder_result = (os.getcwd() + "/" + outdir[:-1] +
                        file_name.replace(".pdf", "").replace(inputdir[:-1], "") + "/")
        ensure_dir(folder_result)
        for idx, page in enumerate(pages):
            page.save(folder_result + "page_" + str(idx) + ".png")
    

def make_noise_image(inputdir, outdir):
    all_files = []
    ensure_dir(outdir)
    all_files = glob.glob(inputdir + "*/*.png")
    thread = NoiseGenerator(inputdir, outdir)
    thread.set_list_files(all_files)
    thread.run()


def run_ocr(path_files):
    len_files = len(path_files)
    execute_time = time.time()
    for idx, path in enumerate(path_files):
        str_out = pytesseract.image_to_string(Image.open(path), lang="vie")
        dir_out = os.path.dirname(path.replace(outdir_noise_image[:-1], ocred_dir[:-1])) + "/"
        name_out = os.path.basename(path).replace(".png", ".txt")
        ensure_dir(dir_out)
        out_file = open(dir_out + name_out, mode="w", encoding="utf-8")
        out_file.write(str_out)
        out_file.close()
        print("\rTime execute: " + str(time.time() - execute_time) 
                + " || Processed: " + str(idx) + "/" + str(len_files), end='\t\t')


def ocr_image(inputdir):
    path_file = glob.glob(inputdir + "*/*.png")
    chunks_path_file = chunks(path_file, int(len(path_file)/int(thread_count/2)))
    with concurrent.futures.ProcessPoolExecutor(max_workers=int(thread_count/2)) as executor:
        executor.map(run_ocr, chunks_path_file)


def normarlize_text(inputdir, outdir):
    list_path = sorted(glob.glob(inputdir + "*/*.txt"))
    start_time = time.time()
    prev_idx = 0
    size_list = len(list_path)
    for idx, path in enumerate(list_path):
        if time.time() - start_time > 1:
            start_time = time.time()
            print("\rFile: " + str(path) + " \tProcessed: "+ str(idx) 
                + "/" + str(size_list) + "\tSpeed: " + str((idx - prev_idx)) + "\t", end="")
            prev_idx = idx

        # path = list_path[0]
        txt_in = open(path, mode="r", encoding="utf-8")
        out_path = path.replace(inputdir[:-1], outdir[:-1])
        ensure_dir(os.path.dirname(out_path) + "/")
        # print(out_path)
        txt_out = open(out_path, mode="w", encoding="utf-8")
        lines = txt_in.readlines()
        for line in lines:
            if len(line.strip()) > 1:
                txt_out.write(line)
        
        txt_out.close()
        txt_in.close()


def delete_map_error(inputdir, outdir, deldir):
    # to delete file cannot mapped  
    count = 0
    ensure_dir(deldir)
    for idx, path in enumerate(glob.glob(inputdir + "*/*.txt")):
        print(path)
        path_pred = path.replace(inputdir[:-1], outdir[:-1])
        gt_file = open(path, mode="r", encoding="utf-8")
        pred_file = open(path_pred, mode="r", encoding="utf-8")
        gt_lines = gt_file.readlines()
        pred_lines = pred_file.readlines()
        num_of_gt_lines = len(gt_lines)
        num_of_pred_line = len(pred_lines)
        if abs(num_of_gt_lines - num_of_pred_line) > 0:
            gt_file.close()
            pred_file.close()
            os.rename(path_pred, deldir + "pred_" + str(count) + ".txt")
            os.rename(path, deldir + "gt_" + str(count) + ".txt")
            count += 1


def merge_to_output(outdir, gt_dir, pred_dir):
    ensure_dir(outdir)
    merge_gt_file = open(outdir + "merged.gt.txt", mode="w", encoding="utf-8")
    merge_pred_file = open(outdir + "merged.pred.txt", mode="w", encoding="utf-8")
    list_file_gt = glob.glob(gt_dir)  
    len_list_file = len(list_file_gt) 
    for idx, gt_path in enumerate(glob.glob(gt_dir + "*/*.txt")):
        pred_path = gt_path.replace(gt_dir[:-1], pred_dir[:-1])
        file_gt = open(gt_path, mode="r", encoding="utf-8")
        file_pred = open(pred_path, mode="r", encoding="utf-8")
        gt_lines = file_gt.readlines()
        pred_lines = file_pred.readlines()
        for line in gt_lines:
            merge_gt_file.write(line.strip() + "\n")

        for line in pred_lines:
            merge_pred_file.write(line.strip() + "\n")

    merge_gt_file.close()
    merge_pred_file.close()


def main():
    # clean directory
    shutil.rmtree(outdir_docx, ignore_errors=True)
    shutil.rmtree(outdir_pdf, ignore_errors=True)
    shutil.rmtree(outdir_image, ignore_errors=True)
    shutil.rmtree(outdir_noise_image, ignore_errors=True)
    shutil.rmtree(ocred_dir, ignore_errors=True)
    shutil.rmtree(pred_dir, ignore_errors=True)
    shutil.rmtree(gt_dir, ignore_errors=True)
    shutil.rmtree(deleted_dir, ignore_errors=True)
    shutil.rmtree(final_out, ignore_errors=True)

    # WRITE TXT source to DOCX file 
    start_time = time.time()
    print("\n[WRITING TXT to DOCX]...")
    create_docx_file(source_path, outdir_docx)
    print("\n[TIME EXECUTE]: " + str(time.time() - start_time))
    
    # CONVERT DOCX file to PDF file
    start_time = time.time()
    print("\n[CONVERTING DOCX to PDF]...")
    convert_docx_to_pdf(outdir_docx, outdir_pdf)
    print("\n[TIME EXECUTE]: " + str(time.time() - start_time))

    # Extract text from PDf to map with OCR result
    start_time = time.time()
    print("\n[EXTRACT TEXT from PDF]...")
    extract_text_from_pdf(outdir_pdf)
    print("\n[TIME EXECUTE]: " + str(time.time() - start_time))

    #Extract Image from PDF
    start_time = time.time()
    print("\n[EXTRACT IMAGE from PDF]...")
    extract_image_from_pdf(outdir_pdf, outdir_image)
    print("\n[TIME EXECUTE]: " + str(time.time() - start_time))

    # NOISE Image
    start_time = time.time()
    print("\n[NOISE IMAGE]...")
    make_noise_image(outdir_image, outdir_noise_image)
    print("\n[TIME EXECUTE]: " + str(time.time() - start_time))

    # Extract Text from Image
    start_time = time.time()
    print("\n[OCR IMAGE]...")
    ocr_image(outdir_noise_image)
    print("\n[TIME EXECUTE]: " + str(time.time() - start_time))

    #Normalize ocr-text and ground-truth-text
    start_time = time.time()
    print("\n[NORMALIZE TXT]...")
    normarlize_text("ocr-ed/", pred_dir)
    normarlize_text(outdir_pdf, gt_dir)
    delete_map_error(pred_dir, gt_dir, deleted_dir)
    print("\n[TIME EXECUTE]: " + str(time.time() - start_time))
    
    #Merge n-files output to one final file 
    start_time = time.time()
    print("\n[MERGE TO OUTPUT]...")
    merge_to_output(final_out, gt_dir, pred_dir)
    print("\n[TIME EXECUTE]: " + str(time.time() - start_time), end="\n"*5)
    print("******       *****     ***    **   *******"
        + "\n**    **   **     **   ****   **   **" 
        + "\n**     **  **     **   ** **  **   ******"
        + "\n**     **  **     **   **  ** **   **"
        + "\n**    **   **     **   **   ****   **"
        + "\n******       *****     **    ***   *******")


if __name__ == "__main__":
    main()  