#!/usr/bin/env python3

import io
import os
import secrets
import sys

import requests
from flask import Flask, render_template, request, send_file, session
from PIL import Image, UnidentifiedImageError

from flask_session import Session


class GD_Scraper():
    def __init__(self, *args, **kwargs):
        self.urls = {
            'lso': 'http://43.129.51.47:9000/gear/',
            'lskr': 'https://lostkr-cdn-image.valofe.com/gear/',
            'lscn': 'http://106.14.0.130:9000/gear/',
            'lse': 'http://203.27.106.27:9000/gear/',
            'lsa': 'http://178.128.23.239:5695/gear/'
            }
        self.save_image = kwargs.get('save_image', False)
        self.write_invalid = kwargs.get('write_invalid', False)
        self.invalid_files = {
            'lso': [],
            'lskr': [],
            'lscn': [],
            'lse': [],
            'lsa': [],
            'custom': []
        }
        self.temp_invalid = []
        self.is_custom = False

        for x in self.invalid_files.keys():
            if os.path.isfile(f'invalid_{x}.txt'):
                with open(f'invalid_{x}.txt') as f:
                    invalid = f.readlines()
                    invalid = [_.strip() for _ in invalid if _.strip()]
                    self.invalid_files[x] = invalid

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
                if not os.path.exists('./texture/'):
                    os.makedirs('./texture/')
                img.save('./texture/' + filename + '.jpg')

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

    def invalid(self, id):
        id = str(id)
        if self.is_custom:
            server = 'custom'
        else:
            server = session['server']
        if not id in self.invalid_files[server]:
            self.invalid_files[server] = [_ for _ in self.invalid_files[server] + [id]]
            if self.write_invalid:
                self.temp_invalid = [_ for _ in self.temp_invalid + [id]]
    
    def invalid_write(self):
        if self.write_invalid:
            if self.is_custom:
                server = 'custom'
            else:
                server = session['server']
            with open(f'invalid_{server}.txt', 'a+') as f:
                text = '\n'
                text += '\n'.join(self.temp_invalid)
                if not text == '\n':
                    f.write(text)

    # My plan is to load 100 gear design per page, not images since some gear requires multiple texture
    # If single item returns 404, then we'll just skip, don't append and just simply leave a blank space
    def load(self, server: str = 'lso', offset: int = 1):
        def check_server(url):
            res = requests.get(url + '1_1.lsc')
            if res.status_code == 404:
                return False
            return True

        self.temp_invalid = []
        self.is_custom = False
        gear_designs = {}

        counter = 1 + (offset - 1) * 25
        end = counter + 24
        custom_url = ''
        server = session['server']

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
                return {'invalid': 404}
            self.is_custom = True

        while counter <= end:
            if self.is_custom:
                if str(counter) in self.invalid_files['custom']:
                    counter += 1
                    continue
            else:
                if str(counter) in self.invalid_files[server]:
                    counter += 1
                    continue

            for x in range(3):
                x = str(x + 1)
                filename = str(counter) + '_' + x

                res = requests.get(url + filename + '.lsc')
                if res.status_code == 200:
                    image_bytes = list(res.content)
                    image_dds = self.convert_lsc(image_bytes)
                    try:
                        image_png = self.convert_dds(image_dds, filename)
                    except UnidentifiedImageError:
                        return {'invalid': 404}
                    gear_designs[filename] = image_png
                else:
                    if x == '1':
                        self.invalid(counter)
                        break
            
            counter += 1
        
        self.invalid_write()
        return gear_designs

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

    options = {
        "lso": "Lost Saga Origin",
        "lskr": "Lost Saga Korea",
        "lscn": "Lost Saga China",
        "lse": "Lost Saga Exotic",
        "lsa":"Lost Saga Aslantia",
        "custom": "Custom Server"
    }

    if not session.get('scraper', None):
        session['scraper'] = GD_Scraper(save_image = True, write_invalid = True)
    
    if not session.get('gear_designs', None):
        session['gear_designs'] = {}

    res = session['scraper'].load(server=server, offset=int(index))
    session['gear_designs'] = session['gear_designs'] | res

    if session['scraper'].is_custom:
        server = 'custom'

    return render_template('index.html', keys=res.keys(), current_page=session['index'], server=server, options=options)

@app.route('/gear/<string:image_id>')
def gear_design_image(image_id):
    if session['gear_designs'].get(image_id, None):
        image = session['gear_designs'][image_id]
        image.seek(0)

        return send_file(image, mimetype='image/jpeg')
    else:
        return 'Image not found', 404

if __name__ == '__main__':
    app.run()