# pdfreduce
Reduce scanned PDF size by converting images to grey/black&amp;white.

Install dependencies as listed in `requirements.txt`.

```
usage: pdfreduce.py [-h] [-j] [-q QUALITY] [-t THUMB_SIZE] [-g GREY_CUTOFF]
                    [-b BW_RATIO] [-s BW_SUPERSAMPLE] [-i LOW] [-I HIGH]
                    inputfile outputfile

Reduce size of images in PDF files.

positional arguments:
  inputfile             input PDF file
  outputfile            output PDF file

optional arguments:
  -h, --help            show this help message and exit
  -j, --use-jpg         Use JPEG to encode images
  -q QUALITY, --quality QUALITY
                        JPEG quality, default 95
  -t THUMB_SIZE, --thumb-size THUMB_SIZE
                        Thunbnail size for checking image type, default 128
  -g GREY_CUTOFF, --grey-cutoff GREY_CUTOFF
                        Grey image threshold, unit is intensity (0-255),
                        default 1.0
  -b BW_RATIO, --bw-ratio BW_RATIO
                        Black&White threshold, range 0-1, default 0.99
  -s BW_SUPERSAMPLE, --bw-supersample BW_SUPERSAMPLE
                        Rate of supersampling before converting to Black&White
                        images, default 1x (off)
  -i LOW, --low LOW     Set pixels with intensity [0, x] to 0, default 10
  -I HIGH, --high HIGH  Set pixels with intensity [255-x, 255] to 255, default
                        35
```

