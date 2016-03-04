#!/usr/bin/env python
# -*- coding: utf-8 -*-
import sys,time,mimetypes,cgi,base64
from os import sep, curdir
from BaseHTTPServer import BaseHTTPRequestHandler, HTTPServer
from algo import Manhattan_ocr

class S(BaseHTTPRequestHandler):
    def _set_headers(self,doctype):
        self.send_response(200)
        self.send_header('Content-type', doctype + '; charset=utf-8')
        self.end_headers()

    def do_GET(self):
        if self.path == '/':
            self.path = 'index.html'
        try:
            doctype, _ = mimetypes.guess_type(self.path)
            self._set_headers(doctype)
            f = open(curdir + sep + self.path)
            self.wfile.write(f.read())
            f.close()
            return
        except IOError:
            self.send_error(404, 'File not found: %s' % self.path)

#    def do_HEAD(self):
#        self._set_headers()
        
    def do_POST(self):
        form = cgi.FieldStorage(
                fp = self.rfile,
                headers = self.headers,
                environ = {'REQUEST_METHOD': 'POST',
                    'CONTENT_TYPE': self.headers['Content-type'],
                    }
                )
        print "Image received."
        imgstr64 = form['image'].value.split(',')[-1]
        # self.send_response(200)
        # self.end_headers()
        self._set_headers('text/html')
        self.wfile.write('Image Received.<br>Running OCR...<br>')
        with open('raw.png','wb') as f:
            f.write(base64.decodestring(imgstr64))
        try:
            self.wfile.write('''
                <br>Your VIN no:
                <br><textarea row="1" col="18">%s</textarea>
                <br><button class="btn btn-lg btn-default" id="go-back">Done</button>
                ''' % Manhattan_ocr.extract(imgstr64))
        except TypeError as e:
            self.wfile.write(e)
            raise

        
def run(server_class=HTTPServer, handler_class=S, port=80):
    server_address = ('', port)
    httpd = server_class(server_address, handler_class)
    print time.asctime(), 'Server starts - %s:%s' % (server_address)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    httpd.server_close()
    print time.asctime(), "Server Stops - %s:%s" % server_address

if __name__ == "__main__":
    if len(sys.argv) == 2:
        run(port=int(sys.argv[1]))
    else:
        run()
