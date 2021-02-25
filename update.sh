git reset --hard
git pull origin master
systemctl daemon-reload
systemctl restart friday.service