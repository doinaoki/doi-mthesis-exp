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

1. 自動データセットの12projectsに対して
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



