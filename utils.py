import os


def chunks(l, n):
    # split list to n-sized chunks
    ret = []
    for i in range(0, len(l), n):
        ret.append(l[i:i+n])
    return ret


def ensure_dir(file_path):
    directory = os.path.dirname(file_path)
    if not os.path.exists(directory):
        os.makedirs(directory)