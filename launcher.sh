echo 'Starting launcher'
cd /home/pi/SD14-Hay-Steamer
echo 'pulling git'
sudo git pull origin
sleep 10
echo 'starting SD14Main.py'
sudo python /home/pi/SD14-Hay-Steamer/SD14Main.py &
