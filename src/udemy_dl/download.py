import os
import sys
import wget
import subprocess
import requests

def download(link, filename):
    try:
        curl_dl(link, filename)
    except OSError:
        if not os.path.exists(filename):
            wget.download(link, filename)
        else:
            raise Exception('Failed to download this lecture')


def curl_dl(link, filename):
    command = ['curl', '-C', '-', link, '-o', filename,'--insecure']

    cert_path = requests.certs.where()
    if cert_path:
        command.extend(['--cacert', cert_path])
    subprocess.call(command)


def dl_progress(num_blocks, block_size, total_size):
    progress = num_blocks * block_size * 100 / total_size
    if num_blocks != 0:
        sys.stdout.write(4 * '\b')
    sys.stdout.write('%3d%%' % (progress))
