# RENAS 再現パッケージ
## 環境構築
### java と python
+ `python >= 3.7`
+ `java`

### パッケージ類
+ mysql
+ pandas
+ numpy
+ simplejson
+ nltk
+ pattern
+ {japanize_}matplotlib
+ pytrec_eval
+ RefactoringMiner2.0.2
#### インストール例
```
brew install mysql
brew install coreutils
pip install pandas
pip install numpy
pip install simplejson
pip install nltk
pip install pattern
pip install matplotlib
pip install japanize-matplotlib
pip install pytrec_eval
```

**RefactoringMiner**

`share/datasets/DetectedRefactorings-WhyWeRefactor/RefactoringMiner-2.0.3/RefactoringMiner-2.0.2`
にあります。
これを自身のパソコンにダウンロードしてください。</br>
その後、RefactoringMinerにパスを通してください。
例としては
'''
vi ~/.zshrc
export PATH="$PATH:**ダウンロードしたRefactoringMinerのパス**/bin"を追加
'''
これで使えるようになると思います。

`pattern` のinstallに失敗する場合、`pip` のパッケージのアップデートを試してください。（wheelのバージョンが悪さしている？）



## 再現手順
時間が非常にかかるので好きなSTEPからやってください。</br>
全て再現するには150GB~200GBくらい必要です </br>
各ファイルは`fs/doi/bthesis/exp/projects/**projects名**`にあります
- STEP 1: projectからRenameリファクタリングを抽出 
- STEP 2: project内の全識別子を取得
- STEP 3: 推薦実施
  - STEP3.1: 予備調査用の推薦
  - STEP3.2: RQ解答用の推薦
- STEP 4：各評価指標の値を計算 & グラフ,表生成
カレントディレクトリは `exp` ディレクトリとします。
```
cd exp
```

## 再現方法
### <span style="color: orange; ">**STEP1** </span> projectからRenameリファクタリングを抽出
ディレクトリ構造
<pre>
  exp
  ├ projects
  │  ├ **プロジェクト名**
  │  │  ├ repo </pre>

1. ディレクトリ構造どおりにディレクトリを作成、配置する。
   + 各projectのrepoは `fs/doi/bthesis/exp/projects/**projects名**`にあります
   + repoの中身はプロジェクトをクローンしたものです
2. カレントディレクトリを`exp`として
    ```　
    python -m renas.getRefactoring **project名へのパス**
    ```
    これによりresult.jsonが作成される。(添字がついているファイル(result0, result1など)は無視してください)
3.  ```　
    python -m script.create_rename_json **project名へのパス**
    ```
    これによりrename.jsonが作成される。



### <span style="color: orange; ">**STEP2** </span>project内の全識別子を取得
ディレクトリ構造
<pre>
  exp
  ├ projects
  │  ├ **プロジェクト名**
  │  │  ├ repo
  │  │  ├ result.json
  │  │  ├ rename.json </pre>

1. ディレクトリ構造どおりにディレクトリを作成、配置する。
2.  ```　
    python -m renas.gitOneArchive **project名へのパス**
    ```
    これによりgoldset.jsonとarchivesディレクトリが作成されます。
    archivesディレクトリは
    <pre>
    archives
    ├ **コミットID**
    │  ├ classRecord.json
    │  ├ exTable.csv.gz
    │  ├ idTable.csv.gz
    │  ├ record.json </pre>
    となっていればokです


### <span style="color: orange; ">**STEP3** </span> 推薦実施
ディレクトリ構造
<pre>
  exp
  ├ projects
  │  ├ **プロジェクト名**
  │  │  ├ repo
  │  │  ├ result.json
  │  │  ├ rename.json
  │  │  ├ goldset.json
  │  │  ├ Archives
              └**コミットID**
                  ├ classRecord.json
                  ├ exTable.csv.gz
                  ├ idTable.csv.gz
                  ├ record.json </pre>

#### <span style="color: pink; ">**STEP3.1** </span> 予備実験用の推薦
予備実験に使用するprojectは4つ. これを**予備実験データセット**とする
<details><summary>4projects</summary>

1. baasbox
2. cordova-plugin-local-notifications
3. morphia
4. spring-integration

</details>


1. 上の4リポジトリで推薦を実施する。
    ```　
    python -m renas.RandomRenas **project名へのパス**
    ```
    これにより\**プロジェクト名**ディレクトリ内に、operations.jsonとrecommend_all_normalize.jsonが作成できていればokです

#### <span style="color: pink; ">**STEP3.2** </span> RQ解答用の推薦
RQ解答に使用するprojectは14つ, そのうち12個を**自動データセット**, 2個を**目視データセット**とする
<details><summary>14projects</summary>

自動データセット
1. testng
2. jackson-databind
3. restli
4. activiti
5. thunderbird-android
6. genie
7. eucalyptus
8. graylog2-server
9. core
10. gnucash-android
11. giraph
12. FBReader

目視データセット
13. ratpack
14. argouml

</details>

1. 上の14projectsで推薦を実施する。
    ```　
    python -m renas.renas **project名へのパス**
    ```
2. 既存手法で14projectsを推薦する
    ```　
    python -m oldRenas.renas **project名へのパス**
    ```
  
手順1、2でこれにより\**プロジェクト名**ディレクトリ内に、
[operations.json, recommend_all_normalize.json, recommend_none, recommend_relation, recommend_relation_normalize]が作成できていればokです


### <span style="color: orange; ">**STEP4** </span> 各評価指標の値を計算 & グラフ,表生成
#### <span style="color: pink; ">**STEP4.1** </span> 予備実験-類似度の調査
**予備実験データセット**を使用する.
<details><summary>予備実験データセット</summary>

1. baasbox
2. cordova-plugin-local-notifications
3. morphia
4. spring-integration

</details>

1. 各projectsに対して
    ```　
    python -m renas.ResearchSimilarity **project名へのパス**
    ```
    を行う。これによりsimilarityディレクトリができる
2. 次に4projectの結果を統合する. パスは4つのprojectのパスを空白で区切って入力する
    ```　
    python -m renas.MergeSimilarity **baasboxへのパス** **cordova-plugin-local-notificationsへのパス** **morphiaへのパス** **spring-integrationへのパス** 
    ```
    結果がprojects/randomMerge/similarity.svgに出力される。

#### <span style="color: pink; ">**STEP4.2** </span> 予備実験-パラメータの調整
**予備実験データセット**を使用する.
<details><summary>予備実験データセット</summary>

1. baasbox
2. cordova-plugin-local-notifications
3. morphia
4. spring-integration

</details>

1. 各projectsに対して
    ```　
    python -m renas.RandomRecommend **project名へのパス**
    ```
    を行う。これによりrandomRankingディレクトリができる
2. 次に4projectの結果を統合する. パスは4つのprojectのパスを空白で区切って入力する
    ```　
    python -m renas.MergeRandomRecommend **baasboxへのパス** **cordova-plugin-local-notificationsへのパス** **morphiaへのパス** **spring-integrationへのパス** 
    ```
    結果はprojects/randomMerge/costbar.csvとcostAll~.csvが出力される。


#### <span style="color: pink; ">**STEP4.3** </span> RQ1調査
projectは14つ, そのうち12個を**自動データセット**, 2個を**目視データセット**とする
<details><summary>14projects</summary>

自動データセット
1. testng
2. jackson-databind
3. restli
4. activiti
5. thunderbird-android
6. genie
7. eucalyptus
8. graylog2-server
9. core
10. gnucash-android
11. giraph
12. FBReader

目視データセット
13. ratpack
14. argouml

</details>

1. 自動データセットのprojectsに対して
    ```　
    python -m renas.integrateRecommend **project名へのパス**
    ```
    を行う。これによりfigureディレクトリができる
2. 次に自動データセット(12project)の結果を統合する. パスは12このprojectのパスを空白で区切って入力する
    ```　
    python -m renas.MergeRandomRecommend **testngへのパス** **jackson-databindへのパス** **restliへのパス** **activitiへのパス** ...他8つのパス
    ```
    結果はprojects/Mergeに各評価指標の出力される。


#### <span style="color: pink; ">**STEP4.4** </span> RQ2調査
projectは14つ, そのうち12個を**自動データセット**, 2個を**目視データセット**とする
<details><summary>14projects</summary>

自動データセット
1. testng
2. jackson-databind
3. restli
4. activiti
5. thunderbird-android
6. genie
7. eucalyptus
8. graylog2-server
9. core
10. gnucash-android
11. giraph
12. FBReader

目視データセット
13. ratpack
14. argouml

</details>

1. 自動データセットのprojectsに対して
    ```　
    python -m renas.RandomRecommend **project名へのパス**
    ```
    を行う。これによりrandomRankingディレクトリができる
2. 次に自動データセット(12project)の結果を統合する. パスは12このprojectのパスを空白で区切って入力する
    ```　
    python -m renas.MergeRandomRecommend **testngへのパス** **jackson-databindへのパス** **restliへのパス** **activitiへのパス** ...他8つのパス
    ```
    結果はprojects/randomMergeに各評価指標の出力される。



### 評価対象リポジトリを用意する
1. `exp` ディレクトリ以下に `projects` ディレクトリを作ってください。
<!-- 2. scrapboxの「Why We Refactor対象リポジトリの全リファクタリング検出」を参考に、RefactoringMiner2.0.2を実行した結果を持ってきてください。`evaluated.txt`に評価した2070コミットのリポジトリ・コミットIDが載っています。 -->
2. `projects` を以下のようなディレクトリ構造にしてください。
   + `evaluated.txt`に書いてあるリポジトリ・コミットの分だけ作れば十分です。ただし、書いてあるコミットIDは**名前変更後**のものです。必要スナップショットは**名前変更前**のもの（=親コミット）です。
   + リポジトリはscrapboxの[Why We Refactor対象リポジトリの全リファクタリング検出](https://scrapbox.io/salab/Why_We_Refactor%E5%AF%BE%E8%B1%A1%E3%83%AA%E3%83%9D%E3%82%B8%E3%83%88%E3%83%AA%E3%81%AE%E5%85%A8%E3%83%AA%E3%83%95%E3%82%A1%E3%82%AF%E3%82%BF%E3%83%AA%E3%83%B3%E3%82%B0%E6%A4%9C%E5%87%BA)のRefactoringMiner2.0.2のものです。`
     + コミットのスナップショットさえあれば十分なので、`repo.tar.bz`だけ持ってきて、そこから必要なスナップショットを `git archive commit-id^` などで取り出すだけでよいです。**名前変更前**のスナップショットを取ることを忘れないようにしてください。
   + `goldset.json` は fs にあります。`home/osumi/mthesis/exp/` 以下に`projects` ディレクトリがあり、そこに各リポジトリ毎に実行結果と共に置いてあります。
+ <pre>
   projects
   ├ **リポジトリ名**
   │   ├ goldset.json
   │   ├ archives
   │   │   ├ **名前変更後のコミットID**
   │   │   │   └ repo
   │   │   │       └ **名前変更前のコミットのスナップショット**</pre>

### 語の形式を統一したTableを作る
+ `table.sh` で各スナップショット毎にテーブルを作成します。全てのスナップショットに対して実行し、tableを作成してください。
   ```
   renas/table.sh path/to/commit-id
   ```
  + 上記の **名前変更後のコミットID**までのpath を引数にしてください。
  + 実行すると`idTable.csv.gz`、`exTable.csv.gz` が生成されます。
    + <pre>
        **名前変更後のコミットID**
        ├ repo/
        ├ idTable.csv.gz
        ├ exTable.csv.gz</pre>
    + 圧縮しているのはそのままだと容量が大きすぎるからです（圧縮なしだと全部で600GBほど使うと思われます）。なおRENASの実行時には解凍する必要はありません。
  + すでにtableがある場合スキップします。強制する場合は `-f` オプションをつけてください。
+ `table.sh`は3つのこと（とgzip圧縮）をまとめてやっています。個別で実行したい場合は以下を参考にしてください。
   1. 関係性解析 `ParseCode` 
      + `idTable.csv` を出力します。
      +  ```
         java -jar AbbrExpansion/out/Parsecode.jar path/to/commit-id
         ```
   2. 省略語展開 `SemanticExpand` 
      + `idTable.csv` を受け取り `exTable.csv` を出力します。
      +  ```
         java -jar AbbrExpansion/out/SematicExpand.jar path/to/commit-id
         ```
   3. 語形変化吸収 `normalize.py`
      + `exTable.csv` を加工して出力します。
      +  ```
         python -m renas.normalize path/to/commit-id
         ```

### RENASを実行する
+ 対象リポジトリ以下全てのスナップショットに対し推薦を実行し結果を出力します。
  + ```
      python -m renas.renas path/to/repo-name
      ```
      + `repo-name/archives` 以下の各スナップショットに推薦(None, Relation, RENAS)を実行し、それぞれの結果 (`recommend_none.json`, `recommend_relation.json`, `recommend_relation_normalize.json`) を出力します。その結果、各リポジトリのディレクトリ構成が以下のようになります。
      + <pre>
          **リポジトリ名**
          ├ archives/
          ├ goldset.json
          ├ recommend_none.json (None)
          ├ recommend_relation.json (Relation)
          ├ recommend_relation_normalize.json (RENAS)</pre>
      + 既に実行結果が存在する場合スキップします。強制する場合は `-f` オプションを付けてください。

### 結果を評価する
#### 個別のリポジトリを評価する
+ 対象リポジトリに手法を適用した結果から、そのリポジトリの各コミット毎の精度をまとめた表 `result.csv` を出力します。
  + ```
      python -m renas.evaluate path/to/repo-name
      ```
      + その結果、各リポジトリのディレクトリ構成が以下のようになります。
      + <pre>
          **リポジトリ名**
          ├ archives/
          ├ goldset.json
          ├ recommend_none.json
          ├ recommend_relation.json
          ├ recommend_relation_normalize.json
          ├ result.csv</pre>

#### 評価結果を結合する
+ 各リポジトリの評価結果 `result.csv` を結合した表 `result_all.csv` を出力するとともに、各結果の統計量( `stderr` に)・分布( `fig/result_all.pdf` )も出力します。
  + ```
      python -m renas.merge {path/to/repo-name}*
      ```
  + 入力は 結合したいリポジトリのpath のリストです。例えば `a/`、`b/`、`c/` ３つのリポジトリの結果を結合したい場合はこれら全てを引数とする必要があります。`projects/` 以下全てのリポジトリについて平均や分布を知るには以下のように `ls -d projects/* ` の結果を渡せばできます。
      + <pre>
          projects/
          ├ **リポジトリ名**
          │  └ result.csv
          ├ **リポジトリ名**
          │  └ result.csv
          ︙</pre>
      + ```
        ls -d projects/* | xargs python -m renas.merge
        ```
+ 実行後、`exp` ディレクトリ以下にファイルが生成されます。
  + <pre>
      exp/
      ├ fig/
      │  └ result_all.pdf
      ├ result_all.csv
      ︙</pre>
+ 平均値は以下のように出力されます。
  + ```
      precision:
      none: 0.184..., relation: 0.327..., relation normalize: 0.296...
      recall:
      none: 0.510..., relation: 0.263..., relation normalize: 0.278...
      fscore:
      none: 0.186..., relation: 0.241..., relation normalize: 0.223...
      exact:
      none: 0.649..., relation: 0.625..., relation normalize: 0.482...
      ```
+ 中央値は以下のように出力されます。
  + ```
      {none, relation, relation normalize}_{precision, recall, fscore, exact} XXXX
      ︙
      ```

## 各ファイルについて
+ `AbbrExpansion`
  + KgExpander
+ `goldset.json`
  + RefactoringMinerの出力からRename関連のものだけを取り出し加工したものです。（評価対象じゃないコミットのデータも混ざってしまってます。消せたら消します）
  + https://doi.org/10.5281/zenodo.7214226 若干カラム名などが違いますがデータについての説明です。
