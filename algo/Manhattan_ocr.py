#!/usr/bin/env python
# -*- coding: utf-8 -*-
import cv2,os,io,json,base64
import numpy as np
from pkg_resources import resource_filename
from pytesseract import image_to_string
from PIL import Image

def is_roi(kp, mask):
    x,y = kp.pt
    return (mask[int(y), int(x)]>0)

def train(sift):
    tr_img = cv2.imread('algo/image/training.jpg', 0)
    mask_img = cv2.imread('algo/image/mask.jpg', 0)
    kp, des = sift.detectAndCompute(tr_img, None)
    valid_idx = [i for i in range(len(kp)) if is_roi(kp[i], mask_img)] 
    return ([kp[i] for i in valid_idx], des[valid_idx, :])

def good_matches(matches):
    good = []
    for m,n in matches:
        if m.distance < 0.7*n.distance:
            good.append(m)
    return good

def orientation(imagebytes):
    sift = cv2.SIFT()
    (kp2, des2) = train(sift)
    index_params = dict(algorithm=0, trees=5)
    search_params = dict(checks=50)
    flann = cv2.FlannBasedMatcher(index_params, search_params)

    try:
        imgarr = np.fromstring(base64.decodestring(imagebytes), np.uint8) 
        ts_img = cv2.imdecode(imgarr, cv2.CV_LOAD_IMAGE_COLOR)
    except:
        print "Illegal file format." 
        with open('log.txt', 'a') as log:
            log.write('Illegal:' + imagebytes)
        return None

    kp1, des1 = sift.detectAndCompute(ts_img, None) 
    matches = flann.knnMatch(des1, des2, k=2)
    good_list = good_matches(matches)
    if len(good_list)>10:
        src_pts = np.float32([kp1[m.queryIdx].pt for m in good_list]).reshape(-1,1,2)
        dst_pts = np.float32([kp2[m.trainIdx].pt for m in good_list]).reshape(-1,1,2)
        M, mask = cv2.findHomography(src_pts, dst_pts, cv2.RANSAC, 5.0)
        matchesMask = mask.ravel().tolist()
  
        warp = cv2.warpPerspective(ts_img, M, (639, 439))
        dst = cv2.bilateralFilter(warp,5, 50, 50)
        cv2.imwrite('orientated.png', dst)
        # cv2.imwrite('test.png',dst)
        img_str = cv2.imencode('.jpg', dst)[1].tostring()
        return img_str
    else:
        print 'Match fail'
        mathcesMask = None
        return None


def extract(pdf_bytes, verbose = True, threshold = 128, delta = 10, log = False):
    ''' Usage:
            Input: bytes string read from image
            Ouput: license information JSON string
            param:
                delta: pixel tolerance
                threshold: binarization threshold
                log: write intermediate result to log.txt
    '''

    resultdict = {}
    table = [0]*threshold + [1]*(256 - threshold)

    #left,top,width,height,mode,language,length
    dataform = {
            # 'VIN': (318, 283, 238, 28, 7, 0, 17)
            'VIN': (304, 283, 280, 32, 7, 0, 17)
            }

    lang=['mon','chi_sim']

    for keys in dataform:
        imgstr = orientation(pdf_bytes)
        if imgstr == None:
            print 'Illegal file format.'
            return None
        img = Image.open(io.BytesIO(imgstr))
        left, top, width, height, mode, lcode, length = dataform[keys]
        pool = [''] * length
        if log:
            a = open('log.txt', 'w')
        for x in xrange(left, left + delta, 2):
            for y in xrange(top - delta * 4, top + delta * 2, 2):
                tmp = img.crop((x, y, x + width, y + height)).convert('L')
                tmp = tmp.point(table, '1')
                tmp.save('tmp.png')
                attempt = image_to_string(tmp,
                        lang = lang[lcode],
                        config = '-psm %d lztd' % mode)
                if len(attempt) == length:
                    for i in xrange(length):
                        pool[i] += attempt[i]
                        if log:
                            a.write(attempt + '\n')
        if log:
            a.close()

        try:
            result = ''.join([max(set(pool[i]), key = pool[i].count) for i in xrange(len(pool))])
        except ValueError:
            result = ''
        resultdict[keys]=result
        print result
    # return json.dumps(resultdict)
    return result

# if __name__=='__main__':
#     with open('image/samples/19188.jpg', 'rb') as f:
#     # with open('image/samples/19188.jpg', 'rb') as f:
#         imagebytes = base64.b64encode(f.read())
#     print extract(imagebytes)
