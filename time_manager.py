from flask import Flask, request, redirect, session
from flask import render_template, send_file, make_response
from tinydb import TinyDB, where, Query
import os, json
from functools import wraps
import matplotlib
matplotlib.use('Agg')
from matplotlib.figure import Figure
import matplotlib.pyplot as plt
import pandas as pd
import base64
from io import BytesIO


app = Flask(__name__)
app.secret_key = 'secret key'
APP_DIR = os.path.dirname(__file__)
DATA_FILE = APP_DIR +  '/data/data.json'
DATA_FILE2 = APP_DIR + '/data/date.json'

db = TinyDB(DATA_FILE)
db2 = TinyDB(DATA_FILE2)

USERLIST = {
    'a' : 'a',
    'user' : 'password',
    'kenzo' : 'aaaa'
    }
    
# ログインしているかチェック
def is_login():
    return 'login' in session

# ログインの試行
def try_login(form):
    user = form.get('user', '')
    password = form.get('pw', '')
    if not user in USERLIST:
        return False
    if USERLIST[user] != password:
        return False
    session['login'] = user
    return True

# ユーザー名を得る
def get_user():
    return session['login'] if is_login() else '未ログイン'

# ログイン状態を判定するデコレーター
def login_required(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        if not is_login():
            return redirect('/')
        return func(*args, **kwargs)
    return wrapper

# あらゆる情報を表示する
def msg(s):
    return render_template('msg.html', msg=s)

# URLのルーティング、ログイン関連の処理
@app.route('/')
def login():
    return render_template('login_form.html')

@app.route('/login/try', methods=['POST'])
def login_try():
    ok = try_login(request.form)
    if not ok: return msg(' ログインに失敗しました ')
    return redirect('/input')

@app.route('/logout')
def logout():
    session.pop('login', None)
    return msg('ログアウトしました')

# 入力画面を表示
@app.route('/input')
@login_required
def input():
    return render_template('input.html')

# 入力情報をアップロード
@app.route('/upload', methods=['POST'])
@login_required
def upload():
    meta = {
        'username': get_user(),
        'date': int(request.form.get('date', '')),
        'hour': int(request.form.get('hour', '0')),
        'minute': int(request.form.get('minute', '0')),
        'action': request.form.get('action', '')
        }
    if (meta['hour'] == 0 & meta['minute'] == 0):
        return msg('時間を指定してください')
    if (meta['action'] == ''):
        return msg('行動を指定してください')
    save_file(meta)
    return msg('登録しました')

# 中間ルーティング
@app.route('/show')
@login_required
def show():
    return render_template('day_choice.html')

# meta情報を時間割合に加工して保存
def save_file(meta):
    meta['time'] = (meta['hour'] * (1/24)) + (meta['minute'] * (1 / (24 * 60)))
    db.insert(meta)
    return db

# 日にちを選び、ユーザー、日付ごとのデータを取得、グラフ表示ルートへ
# 初期化する際に purge を使用して削除
@app.route('/day_choice', methods=['POST'])
@login_required
def get_day():
    day = int(request.form.get('date', ''))
    date_file = db.search((Query().username==get_user()) & (Query().date==day))
    db2.purge()
    db2.insert_multiple(date_file)
    return redirect('/graph')

# 削除機能を付ける
@app.route('/remove')
@login_required
def remove_page():
    return render_template('remove_page.html')

@app.route('/remove_data', methods=['POST'])
@login_required
def remove_data():
    day = int(request.form.get('date', ''))
    db.remove((Query().username==get_user()) & (Query().date==day))
    return msg('削除しました')
    
# 画像を base64 に変換する
def fig_to_base64_img(fig):
    io = BytesIO()
    fig.savefig(io, format="png")
    io.seek(0)
    base64_img = base64.b64encode(io.read()).decode()
    return base64_img

# データを取得し、円グラフに表示する
@app.route('/graph')
def makeplot():
    a = db2.all()
    data_items = [i['action'] for i in a]
    data_rates = [j['time'] for j in a]

    if (sum(data_rates) > 1):
        return msg("1日の時間を超えています。削除してください。")
    
    df = pd.DataFrame(data={"項目名": data_items, "時間": data_rates})

    fig = plt.figure(figsize=(4.5 , 4.5), facecolor="w")

    _df = df.sort_values("時間", ascending=True)

    plt.pie(x=_df["時間"], labels=_df["項目名"], normalize=False,
            autopct="%.2f%%", startangle=90, counterclock=False)
    title = "24hours"
    plt.title(title)
    plt.tight_layout()

    img = fig_to_base64_img(fig)

    return render_template('plot.html', img=img)

    
if __name__=='__main__':
    app.run(debug=True, host='0.0.0.0')
