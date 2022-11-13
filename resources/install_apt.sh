PROGRESS_FILE=/tmp/dependancy_denonavr_in_progress
if [ ! -z $1 ]; then
	PROGRESS_FILE=$1
fi
touch ${PROGRESS_FILE}
echo 0 > ${PROGRESS_FILE}
echo "********************************************************"
echo "*             Installation des dépendances             *"
echo "********************************************************"
sudo apt-get clean
echo 10 > ${PROGRESS_FILE}
sudo apt-get update
echo 20 > ${PROGRESS_FILE}
sudo apt-get install -y python3 python3-pip python3-pyudev python3-requests python3-setuptools python3-dev
echo 30 > ${PROGRESS_FILE}
#sudo pip3 install --upgrade 
echo 40 > ${PROGRESS_FILE}
sudo apt-get -y autoremove
echo 100 > ${PROGRESS_FILE}
echo "********************************************************"
echo "*             Installation terminée                    *"
echo "********************************************************"
rm ${PROGRESS_FILE}
