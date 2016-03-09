#!/usr/bin/env python
# -*- coding: utf-8 -*-
import cv2,io,base64
import numpy as np
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

def trim(str, length):
    for i in xrange(len(str)):
        if str[i] != ' ' and (i +length) < len(str) and ' ' not in str[i:i + length]:
                return str[i:i + length]
    else:
        return ''

def orientation(imagebytes, log = True):
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
        if log:
            cv2.imwrite('orientated.png', dst)
        # cv2.imwrite('test.png',dst)
        img_str = cv2.imencode('.jpg', dst)[1].tostring()
        return img_str
    else:
        print 'Match fail'
        mathcesMask = None
        return None


def extract(pdf_bytes, verbose = True, threshold = 110, delta = 10, log = True):
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
            # 'VIN': (304, 283, 280, 32, 7, 0, 17)
            'VIN': (300, 283, 280, 28, 7, 0, 17)
            }
    idform = {
            # 'name': (240, 120, 240, 80, 7, 1, -1),
            # 'sexuality': (240, 220, 160, 80, 7, 1, 1),
            # 'race': (530, 220, 200, 80, 7, 1, -1),
            # 'year': (240, 320, 160, 80, 7, 0, 4),
            # 'month': (460, 320, 70, 80, 7, 0, -1),
            # 'day': (600, 320, 70, 80, 7, 0, -1),
            # 'address': (240, 440, 340, 160, 7, 1, -1),
            'id': (460, 700, 800, 100, 7, 0, 18)}

    lang=['mon','chi_sim']

    for keys in dataform:
        imgstr = orientation(pdf_bytes)
        img = cv2.imdecode(np.fromstring(imgstr, np.uint8), 0)
        if img == None:
            print 'Illegal file format.'
            return None
        left, top, width, height, mode, lcode, length = dataform[keys]
        pool = [''] * length
        if log:
            a = open('log.txt', 'w')
        for y in xrange(top - delta * 4, top, 2):
            cropimg = img[top:top + height, left:left + width]
            th = cv2.adaptiveThreshold(cropimg, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY,11,np.min(cropimg)/2)
            if log:
                cv2.imwrite('th.jpg', th)
            th2 = th
            contours, hierarchy = cv2.findContours(th2, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)

            bw = np.zeros(th.shape, dtype = np.uint8)
            new = []
            for i in xrange(len(contours)):
                if cv2.contourArea(contours[i]) > 40 or (np.squeeze(contours[i][0])[0] > 0.1 * bw.shape[1] and np.squeeze(contours[i][0])[0] < 0.9 * bw.shape[1]): 
                    new.append(contours[i])
            cv2.drawContours(bw, new, -1, (255,255,255), -1)
            bw[0,:] += 255
            bw[-1,:] += 255
            bw[:,-1] += 255
            bw[:,0] += 255
            if log:
                cv2.imwrite('coned.jpg', bw)

            bw_str = cv2.imencode('.jpg', bw)[1].tostring()
            tmp = Image.open(io.BytesIO(bw_str))
            attempt = image_to_string(tmp,
                    lang = lang[lcode],
                    config = '-psm %d lztd' % mode)
            if len(attempt) == length or trim(attempt, length):
                if log:
                    a.write(attempt + '\n')
                if len(attempt) != length:
                    attempt = trim(attempt, length)
                print attempt
                for i in xrange(length):
                    if attempt[i] != ' ':
                        pool[i] += attempt[i]
        if log:
            a.write(str(pool))
            a.close()

        try:
            result = ''.join([max(set(pool[i]), key = pool[i].count) for i in xrange(len(pool))])
        except ValueError:
            result = ''
        resultdict[keys]=result
        print result
    return resultdict

# if __name__=='__main__':
#     with open('image/samples/19188.jpg', 'rb') as f:
#     # with open('image/samples/19188.jpg', 'rb') as f:
#         imagebytes = base64.b64encode(f.read())
#     print extract(imagebytes)
