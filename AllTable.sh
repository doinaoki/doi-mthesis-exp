PROJECT=$1
REPOPATH="/Users/doinaoki/Documents/GitHub/doi-mthesis-exp/projects/$PROJECT/archives/"

COMMITS=`ls $REPOPATH`
#echo $COMMITS
set -e
for i in $COMMITS
do
    renas/table.sh $REPOPATH$i -f
done
