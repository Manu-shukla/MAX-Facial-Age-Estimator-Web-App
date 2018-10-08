#
# Copyright 2018 IBM Corp. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

import base64
import numpy as np
import requests
import json
import cv2
from flask import Flask, render_template, Response
from gevent import monkey
from io import BytesIO
from PIL import Image
try:
    from flask.ext.socketio import SocketIO, emit
    import Queue as queue
except ImportError:
    from flask_socketio import SocketIO, emit
    import queue

monkey.patch_all()
app = Flask(__name__)
app.config.from_object('config')
app.queue = queue.Queue()
socketio = SocketIO(app)


def draw_label(image, point, label, font=cv2.FONT_HERSHEY_SIMPLEX,
               font_scale=1, thickness=2):
    size = cv2.getTextSize(label, font, font_scale, thickness)[0]
    x, y = point
    cv2.rectangle(image, (x, y - size[1]), (x + size[0], y),
                  (255, 0, 0), cv2.FILLED)
    cv2.putText(image, label, point, font, font_scale,
                (255, 255, 255), thickness)


def base64_to_pil_image(base64_img):
    return Image.open(BytesIO(base64.b64decode(base64_img)))


@app.route("/")
def index():
    """Video streaming home page."""
    return render_template('index.html')


@socketio.on('netin', namespace='/streaming')
def msg(dta):
    emit('response', {'data': dta['data']})


@socketio.on('connected', namespace='/streaming')
def connected():
    emit('response', {'data': 'OK'})


@socketio.on('streamingvideo', namespace='/streaming')
def webdata(dta):
    app.queue.put(dta['data'])


@app.route('/video_feed')
def video_feed():
    """Video streaming route. Put this in the src attribute of an img tag."""
    return Response(gen(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')


def gen():
    skip_frame = 1
    img_idx = 0

    while True:
        input_img = base64_to_pil_image(app.queue.get().split('base64')[-1])
        input_img.save("t1.jpg")

        img_idx += 1
        if img_idx % skip_frame == 0:
            img_pil = np.asarray(Image.open('t1.jpg'))

            img_h, img_w, _ = np.shape(img_pil)

            img_np_frame = img_pil

            img_np_frame = cv2.resize(img_np_frame,
                                      (1024, int(1024*img_h/img_w)))
            img_h, img_w, _ = np.shape(img_np_frame)

            my_files = {'image': open('t1.jpg', 'rb'),
                        'Content-Type': 'multipart/form-data',
                        'accept': 'application/json'}

            r = requests.post('http://localhost:5000/model/predict',
                              files=my_files, json={"key": "value"})

            json_str = json.dumps(r.json())
            data = json.loads(json_str)

            ret_res = data['predictions']

            if len(data['predictions']) <= 0:
                cv2.imwrite('t1.jpg', img_np_frame)
                yield (b'--img_np_frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n'
                       + open('t1.jpg', 'rb').read() + b'\r\n')
            else:
                for i in range(len(ret_res)):
                    age = ret_res[i]['age_estimation']
                    bbx = ret_res[i]['face_box']

                    # draw results
                    x1, y1, w, h = bbx
                    label = "{}".format(age)
                    draw_label(img_np_frame, (int(x1), int(y1)), label)

                    x2 = x1 + w
                    y2 = y1 + h
                    cv2.rectangle(img_np_frame, (int(x1), int(y1)),
                                  (int(x2), int(y2)), (0, 255, 255), 2)

            img_np_frame = cv2.cvtColor(img_np_frame, cv2.COLOR_BGR2RGB)
            cv2.imwrite('t1.jpg', img_np_frame)
            fh = open("./t1.jpg", "rb")
            frame = fh.read()
            fh.close()
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
        else:
            continue
            
            #wavelet quantization of the image for feature enhancement. 
            
 def quantize(self, in_img, thres_percentile):
        sgn_mat = self._create_sgn_mat(in_img)
        abs_img = np.abs(in_img)
        max_val = abs_img.max()+1e-7
        prev_bin_maxs, bin_reps = self._create_bins(abs_img, thres_percentile)
        curr_bin_maxs = self._calc_bin_max(bin_reps, prev_bin_maxs[0,0],max_val)
        diff = prev_bin_maxs-curr_bin_maxs
        cond = 1
        while(cond>lloyd_max_quantizer.CONVERGE_THRES):
            prev_bin_maxs = curr_bin_maxs
            bin_reps = self._calc_bin_rep(abs_img, curr_bin_maxs)
            curr_bin_maxs = self._calc_bin_max(bin_reps,prev_bin_maxs[0,0],max_val)
            diff = prev_bin_maxs - curr_bin_maxs
            cond = np.linalg.norm(diff)

        quantized = np.empty(in_img.shape, dtype=np.uint32)
        for p_idx, val in enumerate(abs_img.flatten()):
            bin_choose = -1
            for b_idx, bin_bound in enumerate(curr_bin_maxs):
                if val < bin_bound:
                    bin_choose = b_idx
                    break

            else:
                bin_choose = len(curr_bin_maxs)-1


if __name__ == "__main__":
    socketio.run(app, host='0.0.0.0', port=7000)
