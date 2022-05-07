# UPS
UPS Monitoring


install :

cd ~/domoticz/plugins

git clone https://github.com/Erwanweb/UPS.git UPS

cd UPS

sudo chmod +x plugin.py

sudo /etc/init.d/domoticz.sh restart

Upgrade :

cd ~/domoticz/plugins/UPS

git reset --hard

git pull --force

sudo chmod +x plugin.py

sudo /etc/init.d/domoticz.sh restart
