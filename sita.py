import sys
import traceback
from mastodon import Mastodon, StreamListener
import os
import re
import datetime

# firestore
from google.cloud import firestore
import urllib

JST = datetime.timezone(datetime.timedelta(hours=+9), 'JST')

youbi = ['日','月','火','水','木','金','土']


def check_test():
    return len(sys.argv) == 2 and sys.argv[1] == "unit_test"

is_test = check_test()

class MastodonMock:
    pass

class StoreMock:
    pass

def create_mastodon_client(test = False):
    if test:
        return MastodonMock()
    else:
        CLIENT_ID = os.environ['CLIENT_ID']
        CLIENT_SECRET = os.environ['CLIENT_SECRET']
        ACCESS_TOKEN = os.environ['ACCESS_TOKEN']
        return Mastodon(
            client_id=CLIENT_ID,
            client_secret=CLIENT_SECRET,
            access_token = ACCESS_TOKEN,
            api_base_url = 'https://mistodon.cloud'
        )

# mastodon
mastodon = create_mastodon_client(is_test)

def create_store(test = False):
    if test:
        return StoreMock()
    else:
        GCP_PROJECT_ID = os.environ['GCP_PROJECT_ID']
        firestore.Client(project=GCP_PROJECT_ID)


def sita_error(st, content, id):
    error_text = f'何かがおかしい可能性があります。エラー：{content}'
    mastodon.status_reply(st, error_text, id, visibility='unlisted')

class Stream(StreamListener):
    def __init__(self):
        super(Stream, self).__init__()
        
    def on_notification(self, notification):
        if notification['type'] == 'mention':
            content = notification['status']['content']
            id = notification['status']['account']['acct']
            st = notification['status']
            content = re.sub('<.*?>', '', content)
            content = re.sub('@sita', '', content)
            content = content.split()
            main(content, st, id)

# firestore
def format_times(time):
        lastTime = time + datetime.timedelta(hours=9)
        lastTime_format = lastTime.strftime("%Y/%m/%d %H:%M")
        #前回からの間隔を計算
        now = datetime.datetime.now().replace(tzinfo=JST)
        interval = now - time.replace(tzinfo=JST)
        total_secs = interval.total_seconds()
        days, amari = divmod(total_secs, 24*3600)
        hours, amari = divmod(amari, 3600)
        minutes, secs = divmod(amari, 60)
        int_format = f'{int(days)}日{int(hours)}時間{int(minutes)}分'
        return {'lastTime': str(lastTime_format), 'interval': str(int_format)}

db = create_store(is_test)

# sita
def add_sita(user, sitakoto):
    doc_ref = db.collection('mist_sita').document(str(user))
    doc = doc_ref.get()
    if type(sitakoto) == list:
        sitakoto = sitakoto[0]
    
    sitakoto = re.sub('[\?\.\/\[\]\-=`~_]', '＿', urllib.parse.quote_plus(sitakoto))
    if len(sitakoto) > 1500:
        return {'error':'sitaの文字数が多すぎます。'}
    try:
        if doc.exists:
            doc_ref.update({
                f'`{sitakoto}`': firestore.ArrayUnion([datetime.datetime.now()]),
            })
        else:
            doc_ref.set({
                f'{sitakoto}': [datetime.datetime.now()],
            })
        sitakoto_dict = doc_ref.get().to_dict()[str(sitakoto)]
        count = len(sitakoto_dict)
        if count < 2 :
            last_time = sitakoto_dict[-1]
        else:
            last_time = sitakoto_dict[-2]
        t = format_times(last_time)
        last_time = t['lastTime']
        interval =  t['interval']
    except:
        count, last_time, interval = 0, 0, 0
        print('例外発生！')
        traceback.print_exc()
    return {'count': count, 'last_time': last_time, 'interval': interval, 'error':'何らかのエラー'}
# のいつ？
def noitsu(user, sitakoto):
    doc_ref = db.collection('mist_sita').document(str(user))
    if type(sitakoto) == list:
        sitakoto = sitakoto[0]
    sitakoto = re.sub('[\?\.\/\[\]\-=`~_]', '＿', urllib.parse.quote_plus(sitakoto))
    try:
        sitakoto_dict = doc_ref.get().to_dict()[str(sitakoto)]
    except KeyError:
        sitakoto_dict = {}
    
    if len(sitakoto_dict) >= 1:
        last_time = sitakoto_dict[-1]
        t = format_times(last_time)
        last_time, interval = t['lastTime'], t['interval']
        return {'count': len(sitakoto_dict), 'last_time': last_time, 'interval': interval}
    else:
        last_time = None
        return {'count': 0}
def deleteall(user):
    db.collection('mist_sita').document(user).delete()


# main

def main(content, st, id):
    if not content or st['visibility'] == 'direct':
        return None
    elif content[0] == 'delete':
        deleteall(id)
        mastodon.status_reply(st, '削除しました！')
    elif len(content[0]) > 400:
        mastodon.status_reply(st,'エラー：sitaの文字数が多すぎます', id, visibility='unlisted')
        sita_error(st, 'sitaの文字数が多すぎます', id)
    elif len(content) >= 2 and content[1] == 'のいつ？': 
        itsu = noitsu(id, content[0])
        if itsu['count'] != 0:
            last_time = itsu['last_time']
            interval = itsu['interval']
            toot = f'最後に{content[0]}したのは、{interval}前（{last_time}）の{itsu["count"]}回目です。'
        else:
            toot = f'あなたはまだ{content[0]}をしたことがないようです。'
    else:
        sita = add_sita(id,content)
        count = sita['count']
        last_time = sita['last_time']
        interval = sita['interval']
        toot = f'おつパオ\n{last_time}以来、{interval}ぶり{count}回目の{content[0]}'
    try:
        reply_text = toot.replace('@', '＠')
        mastodon.status_reply(st, reply_text, id, visibility='unlisted')
    except: 
        mastodon.status_reply(st,'エラー：不明なエラー', id, visibility='unlisted')
        traceback.print_exc()
        return toot

def unit_test():
    print("unit test")

if is_test:
    unit_test()
else:
    try:
        #mastodon.status_post('再稼働しました。 @raito', visibility='unlisted')
        mastodon.stream_user(Stream())
    except mastodon.Mastodon.MastodonMalformedEventError:
        pass
        traceback.print_exc()
    except:
        mastodon.status_post('何らかのエラーが発生し、一時的に動作を停止しました。 @raito', visibility='unlisted')
        traceback.print_exc()


if __name__ == '__main__':
    pass