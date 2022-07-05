# mistodon sita bot

したことを記録するmastodonのbot、[@sita@mistodon.cloud](https://mistodon.cloud/@sita)です。

heroku上にホストされています。

常時起動し通知を待ち受け、メンションがあれば処理を行って返信します。

使い方は[@sita@mistodon.cloud](https://mistodon.cloud/@sita)の固定トゥートを参照。


## スペシャルサンクス

デバッグに協力していただいた雲鯖のみなさん

CC0ライセンスで公開されています。

## 管理人

[@raito@mistodon.cloud](https://mistodon.cloud/@raito)

## アップデート

- 1.1
  - 実行環境を自宅raspberrypiからherokuに移行し、可用性が向上しました。
- 1.2
  - karino2氏の協力により、少し変わりました
- 1.3(WIP) 2022/07
  - sitaのまとめ機能を実装予定です
  - 完成品イメージ：あなたが初めて{sitakoto}したのは{n}日前の{y}年{m}月{d}日で、{y}年{m}月{d}日の{n}回目まで、1週間平均{i}回です。