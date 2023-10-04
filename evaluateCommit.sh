COMMIT=$2
FOLDERPATH=$1
REPOPATH="$FOLDERPATH/repo"
RESULTPATH="$FOLDERPATH/result.json"
COMMITPATH="$FOLDERPATH/archives/$COMMIT"

RefactoringMiner -c $REPOPATH $COMMIT >> $RESULTPATH
python3 -m script.create_rename_json $FOLDERPATH
python3 -m renas.gitArchive $FOLDERPATH
sh renas/table.sh $COMMITPATH
python3 -m renas.renas $FOLDERPATH -f
python3 -m renas.evaluate $FOLDERPATH -f
python3 -m renas.integrateRecommend $FOLDERPATH
