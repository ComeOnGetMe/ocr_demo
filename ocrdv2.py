#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os,sys,io,json
from PIL import Image
from pytesseract import image_to_string

def ocr(pdf_bytes):
    resultdict = {}
    threshold = 85 
    # pixel tolerance
    delta = 5
    # image binarization table 
    table = [0]*threshold + [1]*(256 - threshold)

    #left,top,width,height,mode,language,length
    dataform = {
            #'VIN': (318, 283, 238, 28, 7, 0, 17)
            'VIN': (304, 283, 238, 32, 7, 0, 17)
            }

    #lang=['-l eng','-l chi_sim','digits']
    lang=['eng','chi_sim']

    for keys in dataform:
        img = Image.open(io.BytesIO((pdf_bytes)))
        left, top, width, height, mode, lcode, length = dataform[keys]
        pool = [''] * length
        a = open('log.txt', 'w')
        for x in xrange(left - delta * 2, left + delta * 2, 2):
            for y in xrange(top - delta * 2, top + delta * 2, 2):
                tmp = img.crop((x, y, x + width, y + height)).convert('L')
                tmp = tmp.point(table, '1')
                attempt = image_to_string(tmp,
                        lang = lang[lcode],
                        config = '-psm %d' % mode)
                if len(attempt) == length:
                    for i in xrange(length):
                        pool[i] += attempt[i]
                        a.write(attempt + '\n')
        a.close()

        result = ''.join([max(set(pool[i]), key = pool[i].count) for i in xrange(len(pool))])
        resultdict[keys]=result
    return json.dumps(resultdict).decode('unicode-escape').encode('utf8')

with open('image/5.jpg','rb') as img:
    image_bytes = img.read()
print ocr(image_bytes)
