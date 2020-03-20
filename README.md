# pdfreduce
Reduce scanned PDF size by converting images to grey/black&amp;white.

This is NOT effective for mostly color or already CCITT-Group5-encoded PDFs.

Install dependencies as listed in `requirements.txt`.

```
usage: pdfreduce.py [-h] [-j JOBS] [-J] [-q QUALITY] [-t SIZE] [-g X] [-b X]
                    [-s X] [-i LOW] [-I HIGH]
                    inputfile outputfile

Reduce size of images in PDF files.

positional arguments:
  inputfile             input PDF file
  outputfile            output PDF file

optional arguments:
  -h, --help            show this help message and exit
  -j JOBS, --jobs JOBS  Parallel job number
  -J, --use-jpg         Use JPEG to encode images
  -q QUALITY, --quality QUALITY
                        JPEG quality, default 95
  -t SIZE, --thumb-size SIZE
                        Thunbnail size for checking image type, default 128
  -g X, --grey-cutoff X
                        Grey image threshold, unit is intensity (0-255),
                        default 1.0
  -b X, --bw-ratio X    Black&White threshold, range 0-1, default 0.92
  -s X, --bw-supersample X
                        Rate of supersampling before converting to Black&White
                        images, default 1.5x
  -i LOW, --low LOW     Set pixels with intensity [0, x] to 0, default 10
  -I HIGH, --high HIGH  Set pixels with intensity [255-x, 255] to 255, default
                        35
```

