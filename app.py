#!/usr/bin/env python3

import concurrent.futures
import io
import os
import pathlib
import secrets
import shutil
import sys

import requests
from flask import Flask, render_template, request, send_file, session
from PIL import Image, UnidentifiedImageError

from flask_session import Session


class GD_Scraper():
    def __init__(self, *args, **kwargs):
        self.urls = {
            'lso': 'http://43.129.51.47:9000/gear/',
            'lskr': 'http://lostkr-cdn-image.valofe.com/gear/',
            'lscn': 'http://106.14.0.130:9000/gear/',
            'lse': 'http://203.27.106.27:9000/gear/',
            'lsa': 'http://patch.lostsagacdn.com:10095/gear/'
            }
        self.save_image = kwargs.get('save_image', False)
        self.is_custom = False
        self.server = ''

    # https://github.com/Trisnox/lsc2dds-py
    def convert_lsc(self, array):
        result = []
        for byte in array:
            temp = (byte & 0x7) << 0x5
            byte >>= 0x3
            byte |= temp
            byte ^= 0xff
            result.append(byte)

        return result

    def convert_dds(self, image, filename = 'unknown'):
        with Image.open(io.BytesIO(bytearray(image))) as img:
            # Appearantly the texture had transparency? Besides the game only allows you to upload jpg so...
            img = img.convert('RGB') 

            if self.save_image:
                if self.is_custom:
                    server_name = 'custom'
                else:
                    server_name = self.server

                img.save(f'./texture_{server_name}/' + filename + '.jpg')

            texture_image = io.BytesIO()
            img.save(texture_image, format='jpeg')
            texture_image.name = filename

        return texture_image
    
    # testing
    def load_binary(self):
        images = []
        for x in range(5):
            x += 1
            x = str(x)

            filename = x + '_1'

            with open(f'testing/{x}_1.lsc', 'rb') as f:
                image_bytes = list(f.read())

            image_dds = self.convert_lsc(image_bytes)
            image = self.convert_dds(image_dds, filename)
            images = [_ for _ in images + [image]]
        
        return images

    # My plan is to load 100 gear design per page, not images since some gear requires multiple texture
    # If single item returns 404, then we'll just skip, don't append and just simply leave a blank space
    def load(self, server: str = 'lso', offset: int = 1):
        def check_server(url):
            res = requests.get(url + '1_1.lsc')
            if res.status_code == 404:
                return False
            return True

        def process(key):
            gear_designs_bytes = {}
            for url, filename in key.items():
                try:
                    res = requests.get(url)
                except requests.exceptions.ConnectTimeout:
                    continue

                if res.status_code == 200:
                    image_bytes = list(res.content)
                    gear_designs_bytes = gear_designs_bytes | {filename: image_bytes}
                else:
                    if filename[-1] == '1':
                        return None
            return gear_designs_bytes

        def process_bytes(filename, image_bytes):
            image_dds = self.convert_lsc(image_bytes)
            try:
                image_png = self.convert_dds(image_dds, filename)
                return {filename: image_png}
            except UnidentifiedImageError:
                return None

        self.server = server

        cache = session['cache'].get(server, [])
        if offset in cache:
            return {}, True
        
        cache = [_ for _ in cache + [offset]]
        session['cache'][server] = cache

        self.is_custom = False
        gear_designs_bytes = {}
        gear_designs = {}

        counter = 1 + (offset - 1) * 25
        end = counter + 24
        custom_url = ''
        server = session['server']
        urls = []

        url = self.urls.get(server, None)
        if not url and server.startswith('http'):
            if not server.endswith('/'):
                custom_url = server + '/gear/'
            else:
                custom_url = server + 'gear/'
        elif not url and server[0].isdigit():
            custom_url = 'http://' + server + '/gear/'
        elif not url:
            custom_url = 'https://' + server + '/gear/'
        
        if custom_url:
            url = custom_url
            checks = check_server(custom_url)

            if not checks:
                return {'invalid': 404}, False
            self.is_custom = True

        while counter <= end:
            num = str(counter)
            req_urls = [{
                url + num + '_1.lsc': num +'_1',
                url + num + '_2.lsc': num +'_2',
                url + num + '_3.lsc': num +'_3'
            }]
            urls = [_ for _ in urls + req_urls]
            
            counter += 1

        # turns out slower because it waits for the url first, then convert
        # what if... we convert it on the go?
        # idk if this slower, because I need a constant fast internet and processor to do so
        # but anyways, now it's at least 3x faster
        with concurrent.futures.ThreadPoolExecutor(max_workers=len(urls)*2) as executor:
            result = list(executor.map(process, urls))
            for x in result:
                if x is not None:
                    gear_designs_bytes = gear_designs_bytes | x
        
        if self.save_image:
            if self.is_custom:
                server_name = 'custom'
            else:
                server_name = server

            if not os.path.exists(f'./texture_{server_name}/'):
                os.makedirs(f'./texture_{server_name}/')
        
        if len(gear_designs_bytes) == 0:
            return {}, False

        with concurrent.futures.ThreadPoolExecutor(max_workers=len(gear_designs_bytes)) as executor:
            result = list(executor.map(process_bytes, gear_designs_bytes.keys(), gear_designs_bytes.values()))
            for x in result:
                if x is not None:
                    gear_designs = gear_designs | x

        return gear_designs, False

# Temporal solution until I figure out how to detect older version of session and then remove and restart when it does
# Why? Because the class variables are basically static, which cause it to act as if this code was using the older version when it does not
dirpath = pathlib.Path('flask_session')
if dirpath.exists() and dirpath.is_dir():
    shutil.rmtree(dirpath)

if getattr(sys, 'frozen', False):
    template_folder = os.path.join(sys._MEIPASS, 'templates')
    static_folder = os.path.join(sys._MEIPASS, 'static')
    app = Flask(__name__, template_folder=template_folder, static_folder=static_folder)
else:
    app = Flask(__name__, template_folder='templates', static_folder='static')

app.secret_key = secrets.token_hex(32)
app.config['SESSION_PERMANENT'] = False
app.config['SESSION_TYPE'] = 'filesystem'
Session(app)

@app.context_processor
def inject_enumerate():
    return dict(enumerate=enumerate)

@app.route('/')
def index():
    server = request.args.get('server')
    index = request.args.get('index')
    if server is None:
        server = 'lso'
    if index is None:
        index = '1'

    session['server'] = server
    session['index'] = index

    if not session.get('version_check'):
        session['version_check'] = False

    if not session.get('cache'):
        session['cache'] = {
            'lso': [],
            'lskr': [],
            'lscn': [],
            'lse': [],
            'lsa': []
        } # custom will not be made since it's dynamic. If I were to, I'd use the self.is_custom variable to check

    options = {
        "lso": "Lost Saga Origin",
        "lskr": "Lost Saga Korea",
        "lscn": "Lost Saga China",
        "lse": "Lost Saga Exotic",
        "lsa":"Lost Saga Aslantia",
        "custom": "Custom Server"
    }

    version = "v2.1"
    if not session.get('version_check'):
        session['version_check'] = True

        try:
            response = requests.get("https://api.github.com/repos/Trisnox/Lost-Saga-GD-Scraper/releases/latest").json()
            if version != response['tag_name']:
                session['latest_version_check'] = True
            else:
                session['latest_version_check'] = False
        except requests.ConnectionError:
            pass

    if not session.get('scraper', None):
        session['scraper'] = GD_Scraper(save_image = True)
    
    if not session.get('gear_designs', None):
        session['gear_designs'] = {
            'lso': {},
            'lskr': {},
            'lscn': {},
            'lse': {},
            'lsa': {},
            'custom': {}
        }
        # session['gear_designs']['merged'] = {}

    res, cached = session['scraper'].load(server=server, offset=int(index))
    if not cached:
        session['gear_designs'][server][index] = res
        # session['gear_designs']['merged'] = session['gear_designs']['merged'] | res

    if session['scraper'].is_custom:
        server = 'custom'

    return render_template('index.html', keys=session['gear_designs'][server][index].keys(), current_page=session['index'], server=server, options=options, version=version, latest=session['latest_version_check'])

@app.route('/gear/<string:image_id>')
def gear_design_image(image_id):
    if session['gear_designs'][session['server']][session['index']].get(image_id, None):
        image = session['gear_designs'][session['server']][session['index']][image_id]
        image.seek(0)

        return send_file(image, mimetype='image/jpeg')
    else:
        return 'Image not found', 404

if __name__ == '__main__':
    app.run()
