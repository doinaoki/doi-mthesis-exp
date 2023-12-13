PROJECT=$1
COMMIT="0777129fe2b3af75ec16d383b556e54fbd86c634"
FILEPATH="/Users/doinaoki/Documents/GitHub/doi-mthesis-exp/projects/$PROJECT/repo"
STOREPATH="/Users/doinaoki/Documents/GitHub/doi-mthesis-exp/projects/$PROJECT/result.json"
echo $PROJECT
cd $FILEPATH
cp /dev/null $STOREPATH
LOGCOMMIT=`git log | grep -n commit | awk '{ print $2 }'`
COMMITBEFORE=1
COMMITAFTER=93100
NOWCOMMIT=0
echo "{" >> $STOREPATH
echo "\"commits\": [" >> $STOREPATH
for i in ${LOGCOMMIT}
do
    if [ ${#i} -eq 40 ]; then
        if [ $COMMITBEFORE -lt $NOWCOMMIT ]; then
            if [ $COMMITAFTER -ge $NOWCOMMIT ]; then
                echo $NOWCOMMIT
                RefactoringMiner -c $FILEPATH $i | sed '$d' | sed '$d' | tail +3 >> $STOREPATH
                #RM=`RefactoringMiner -c $FILEPATH $i`
                #wc -l $RM | echo
                if [ $COMMITAFTER -eq $NOWCOMMIT ]; then
                    echo "}" >> $STOREPATH
                else
                    echo "}," >> $STOREPATH
                fi
            fi
        fi
        NOWCOMMIT=$(($NOWCOMMIT + 1))
    fi
done
echo "]}" >> $STOREPATH
