from ntpath import join
import sys
import traceback
from mastodon import Mastodon, StreamListener
import os
import re
import datetime
import unittest

# firestore
from google.cloud import firestore
import urllib

JST = datetime.timezone(datetime.timedelta(hours=+9), 'JST')

youbi = ['日','月','火','水','木','金','土']


def check_test():
    return len(sys.argv) == 2 and sys.argv[1] == "unit_test"

is_test = check_test()

def create_mastodon_client(test = False):
    if test:
        return {}
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

def create_db(test = False):
    if test:
        return {}
    else:
        GCP_PROJECT_ID = os.environ['GCP_PROJECT_ID']
        return firestore.Client(project=GCP_PROJECT_ID)


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

db = create_db(is_test)

class Store:
    """
    db関連の処理をするクラス
    今のところはlookupしか実装していない。 
    """
    def __init__(self, db):
        self.db = db
    
    def find_doc(self, user):
        return db.collection('mist_sita').document(str(user))
    
    # sitakotoは文字列（リストの時に最初の要素にするのは呼び出し側の責任）
    def lookup(self, user, sitakoto):
        doc_ref = self.find_doc(user)
        return doc_ref.get().to_dict()[str(sitakoto)]





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
def noitsu(user, sitakoto, store):
    if type(sitakoto) == list:
        sitakoto = sitakoto[0]
    sitakoto = re.sub('[\?\.\/\[\]\-=`~_]', '＿', urllib.parse.quote_plus(sitakoto))
    try:
        sitakoto_dict = store.lookup(user, sitakoto)
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
# まとめ
def matome(user, sitakoto, store):
    sitakoto = sitakoto[0] if type(sitakoto) == list else sitakoto
    sitakoto = re.sub('[\?\.\/\[\]\-=`~_]', '＿', urllib.parse.quote_plus(sitakoto))
    try:
        sitakoto_dict = store.lookup(user, sitakoto)
    except KeyError:
        sitakoto_dict = {}

    if len(sitakoto_dict) >= 2:
        first, last = sitakoto_dict[0], sitakoto_dict[-1]
        first_t, last_t =  first.strftime("%Y/%m/%d"), last.strftime("%Y/%m/%d")
        count = len(sitakoto_dict)
        from_first = (last - first).days if (first-last).days != 0 else 1
        from_last = (datetime.datetime.now() - last).days
        week_ave = format(count / (from_first/7), '.3f')
        m = {
            'first': first_t,  
            'last': last_t, 
            'count': count,
            'from_first': from_first,
            'from_last': from_last,
            'week_ave': week_ave
            }
        if len(sitakoto_dict) >= 10:
            before_10 = sitakoto_dict[-10]
            before_10_t = before_10.strftime("%Y%m%d")
            from_10 = (last - before_10).days if (last - before_10) != 0 else 1
            from_10_ave = format(10 / (from_10/7), '.3f') 
            m.update({
                'before_10': before_10_t,
                'from_10_ave': from_10_ave
            })
        return m
    elif len(sitakoto_dict) == 1:
        first = sitakoto_dict[0]
        first_t = first.strftime("%Y/%m/%d %H:%M")
        from_first = (datetime.datetime.now() - first).days
        return {
            'first': first_t,
            'from_first': from_first,
            'count': 1
            }
    elif len(sitakoto_dict) == 0:
        return {'count': 0}
def deleteall(user):
    db.collection('mist_sita').document(user).delete()


# main

def main(content, st, id):
    store = Store(db)
    toot = ''
    if not content or st['visibility'] == 'direct':
        return None
    elif content[0] == 'delete':
        deleteall(id)
        mastodon.status_reply(st, '削除しました！')
    elif len(content[0]) > 400:
        sita_error(st, 'sitaの文字数が多すぎます', id)
        return None
    elif len(content) >= 2 and content[1] == 'のいつ？': 
        itsu = noitsu(id, content[0], store)
        if itsu['count'] != 0:
            last_time = itsu['last_time']
            interval = itsu['interval']
            toot = f'最後に{content[0]}したのは、{interval}前（{last_time}）の{itsu["count"]}回目です。'
        else:
            toot = f'あなたはまだ{content[0]}をしたことがないようです。'
    elif len(content) >= 2 and content[1] == 'まとめ':
        m = matome(id, content, store)
        if m['count'] == 1:
            toot = f'{content[0]}のまとめ\n'\
                    + f'初回：{m["first"]}({m["from_first"]}日前)'
        elif m['count'] == 0:
            toot = f'あなたはまだ{content[0]}をしたことがないようです。'
        else:
            toot = f'{content[0]}のまとめ\n'\
                    + f'初回：{m["first"]}({m["from_first"]}日前)'\
                    + f'最新：{m["last"]}({m["from_last"]})'\
                    + f'した回数：{m["count"]}回'\
                    + f'1週間の平均回数（全期間）：{m["week_ave"]}'       
            if m['count'] >= 10:
                toot = [toot]
                toot.append(f'1週間の平均回数（最新10回分）：{m["from_10_ave"]}')
            
        if type(toot) == list:
            toot = ''.join(toot)

    else:
        sita = add_sita(id,content)
        count = sita['count']
        last_time = sita['last_time']
        interval = sita['interval']
        toot = f'おつパオ\n{last_time}以来、{interval}ぶり{count}回目の{content[0]}'
    try:
        reply_text = toot.replace('@', '＠')
        if len(reply_text) >= 450:
            reply_text = reply_text[:450] + '...'
        mastodon.status_reply(st, reply_text, id, visibility='unlisted')
    except: 
        mastodon.status_reply(st,'エラー：不明なエラー', id, visibility='unlisted')
        traceback.print_exc()
        return toot


class StoreMock:
    def __init__(self):
        self.returnValue = {}

    def lookup(self, user, sitakoto):
        self.user = user
        self.sitakoto = sitakoto
        return self.returnValue


class TestSitaKoto(unittest.TestCase):
    def setUp(self):
        self.store = StoreMock()

    def test_firstTime_Normal(self):
        store = self.store
        actual = noitsu("karino2012", "hogehoge", store)
        self.assertEqual('karino2012', store.user)
        self.assertEqual('hogehoge', store.sitakoto)
        self.assertEqual(0, actual['count'])

    def test_firstTime_Magic(self):
        store = self.store
        noitsu("karino2012", "hoge.ika", store)
        self.assertEqual('hoge＿ika', store.sitakoto)

    def test_secondTime(self):
        store = self.store
        tenMinutesBefore = datetime.datetime.now().replace(tzinfo=JST)-datetime.timedelta(minutes=10)
        store.returnValue = [tenMinutesBefore]
        actual = noitsu("karino2012", "hogehoge", store)
        self.assertEqual(1, actual['count'])
        self.assertEqual(actual['interval'], '0日0時間10分')


def unit_test():
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(TestSitaKoto)
    runner = unittest.TextTestRunner()
    runner.run(suite)

if is_test:
    unit_test()
else:
    try:
        mastodon.stream_user(Stream())
    except mastodon.Mastodon.MastodonMalformedEventError:
        pass
        traceback.print_exc()
    except:
        mastodon.status_post('何らかのエラーが発生し、一時的に動作を停止しました。 @raito', visibility='unlisted')
        traceback.print_exc()


if __name__ == '__main__':
    pass