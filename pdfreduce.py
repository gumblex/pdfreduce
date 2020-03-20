#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import io
import os
import sys
import zlib
import argparse
import contextlib
import concurrent.futures

import pdfrw
import numpy as np
from PIL import Image, TiffImagePlugin

import imgautocompress


__version__ = '0.2'


def xobj_getimg(obj):
    if obj['/Subtype'] != '/Image':
        return
    size = (obj['/Width'], obj['/Height'])
    data = obj.stream.encode('latin-1')
    if obj['/ColorSpace'] == '/DeviceRGB':
        mode = "RGB"
    elif obj['/ColorSpace'] == '/DeviceGray':
        mode = "L"
    else:  # can't support other color spaces
        return
    if '/Filter' in obj:
        if obj['/Filter'] == '/FlateDecode':
            return Image.frombytes(mode, size, zlib.decompress(data))
        elif obj['/Filter'] in ('/DCTDecode', '/JPXDecode'):
            return Image.open(io.BytesIO(data))
        else:  # skip CCITTFaxDecode and JBIG2Decode
            return
    else:
        return Image.frombytes(mode, size, data)


def encode_xobj(im, xobj, name, img_format, **kwargs):
    N = pdfrw.PdfName
    buf = io.BytesIO()
    xobj_new = xobj.copy()
    width, height = im.size
    if name:
        xobj_new[N('Name')] = name
    xobj_new[N('Width')] = width
    xobj_new[N('Height')] = height
    xobj_new[N('BitsPerComponent')] = 8
    with contextlib.suppress(KeyError):
        del xobj_new['/DecodeParms']
    if im.mode in '1L':
        xobj_new[N('ColorSpace')] = N('DeviceGray')
    else:
        xobj_new[N('ColorSpace')] = N('DeviceRGB')
    if img_format == 'group4':
        im.save(buf, 'TIFF', compression='group4', **kwargs)
        out_im_load = Image.open(buf)
        strip_offsets = out_im_load.tag_v2[TiffImagePlugin.STRIPOFFSETS]
        strip_bytes = out_im_load.tag_v2[TiffImagePlugin.STRIPBYTECOUNTS]
        assert len(strip_offsets) == len(strip_bytes) == 1
        buf.seek(strip_offsets[0])
        xobj_new[N('BitsPerComponent')] = 1
        xobj_new[N('ImageMask')] = pdfrw.PdfObject('true')
        xobj_new[N('Filter')] = N('CCITTFaxDecode')
        xobj_new[N('DecodeParms')] = pdfrw.PdfDict(
            K=-1, Columns=width, Rows=height, BlackIs1=pdfrw.PdfObject("true")
        )
        xobj_new.stream = buf.read(strip_bytes[0]).decode('latin-1')
    elif img_format == 'jpg':
        im.save(buf, 'JPEG', **kwargs)
        xobj_new[N('Filter')] = N('DCTDecode')
        xobj_new.stream = buf.getvalue().decode('latin-1')
    elif img_format == 'jp2k':
        im.save(buf, 'JPEG2000', **kwargs)
        xobj_new[N('Filter')] = N('JPXDecode')
        xobj_new.stream = buf.getvalue().decode('latin-1')
    elif img_format == 'png':
        xobj_new[N('Filter')] = N('FlateDecode')
        data = zlib.compress(im.tobytes('raw'), 9)
        xobj_new.stream = data.decode('latin-1')
    else:
        raise NotImplementedError(img_format)
    return xobj_new


def encode_img(im, xobj, name=None, use_jpg=True, quality=95, thumb_size=128,
               grey_cutoff=1, bw_ratio=0.99, bw_supersample=1, low=10, high=40):
    orig_size = len(xobj.stream)
    out_im = imgautocompress.auto_downgrade(
        im, thumb_size, grey_cutoff, bw_ratio, bw_supersample)
    width, height = out_im.size
    if out_im.mode == '1':
        return encode_xobj(out_im, xobj, name, 'group4')
    if low or high:
        pixels = np.array(out_im)
        pixels = np.where(pixels<=low, 0, pixels)
        pixels = np.where(pixels>=(255-high), 255, pixels)
        out_im = Image.fromarray(pixels)
    if out_im.mode[0] == 'L':
        return encode_xobj(out_im, xobj, name, 'png')
    if im.format.startswith('JPEG') or not use_jpg:
        xobj_new = encode_xobj(out_im, xobj, name, 'png')
    else:
        xobj_new = encode_xobj(
            out_im, xobj, name, 'jpg', quality=95, optimize=True)
    if len(xobj_new.stream) > orig_size:
        if out_im.mode == im.mode:
            return xobj
        else:
            return encode_xobj(out_im, xobj, name, 'png')
    else:
        return xobj_new


def _optimize_xobjs(xobjs, encode_params):
    for name, obj in xobjs.items():
        im = xobj_getimg(obj)
        if im is None:
            continue
        xobjs[name] = encode_img(im, obj, name, **encode_params)
        #print(xobjs[name]['/Filter'])


def optimize_pdf(filename, output, encode_params, parallel=None):
    pdf = pdfrw.PdfReader(filename)
    parallel = parallel or os.cpu_count()
    with concurrent.futures.ThreadPoolExecutor(max_workers=parallel) as executor:
        futures = []
        completed = 0
        for page in pdf.pages:
            xobjs = page['/Resources'].get('/XObject')
            if not xobjs:
                continue
            futures.append(executor.submit(_optimize_xobjs, xobjs, encode_params))
        total = len(futures)
        for fut in concurrent.futures.as_completed(futures):
            completed += 1
            print('%d/%d %d%%\r' % (completed, total, 100*completed/total), end='')
        print('Completed. Writing pdf...')
    writer = pdfrw.PdfWriter(output, trailer=pdf)
    writer.write()


def main(argv):
    parser = argparse.ArgumentParser(description="Reduce size of images in PDF files.")
    parser.add_argument(
        "-j", "--jobs", type=int, default=0, help="Parallel job number")
    parser.add_argument(
        "-J", "--use-jpg", action='store_true', help="Use JPEG to encode images")
    parser.add_argument(
        "-q", "--quality", type=int, default=95, help="JPEG quality, default 95")
    parser.add_argument(
        "-t", "--thumb-size", type=int, default=128, metavar='SIZE',
        help="Thunbnail size for checking image type, default 128")
    parser.add_argument(
        "-g", "--grey-cutoff", type=float, default=1, metavar='X',
        help="Grey image threshold, unit is intensity (0-255), default 1.0")
    parser.add_argument(
        "-b", "--bw-ratio", type=float, default=0.92, metavar='X',
        help="Black&White threshold, range 0-1, default 0.92")
    parser.add_argument(
        "-s", "--bw-supersample", type=float, default=1.5, metavar='X',
        help="Rate of supersampling before converting to Black&White images, default 1.5x")
    parser.add_argument(
        "-i", "--low", type=float, default=10,
        help="Set pixels with intensity [0, x] to 0, default 10")
    parser.add_argument(
        "-I", "--high", type=float, default=35,
        help="Set pixels with intensity [255-x, 255] to 255, default 35")
    parser.add_argument("inputfile", help="input PDF file")
    parser.add_argument("outputfile", help="output PDF file")
    args = parser.parse_args(argv)

    params = {
        'use_jpg': args.use_jpg,
        'quality': args.quality,
        'thumb_size': args.thumb_size,
        'grey_cutoff': args.grey_cutoff,
        'bw_ratio': args.bw_ratio,
        'bw_supersample': args.bw_supersample,
        'low': args.low,
        'high': args.high,
    }
    optimize_pdf(args.inputfile, args.outputfile, params)
    return 0


if __name__ == '__main__':
    main(sys.argv[1:])
