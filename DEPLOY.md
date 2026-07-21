# VPS Deployment (Ubuntu/Debian)
# ================================

## 1. Install dependencies
sudo apt update && sudo apt install -y python3 python3-pip python3-venv git

## 2. Clone the repo
cd /opt
sudo git clone https://github.com/itachiplub-cloud/unoitachi4.git
cd unoitachi4

## 3. Create virtual environment
python3 -m venv venv
source venv/bin/activate

## 4. Install Python packages
pip install -r requirements.txt

## 5. Configure environment
cp .env.example .env
nano .env   # Add your BOT_TOKEN and MONGO_URI

## 6. Run directly (quick test)
python main.py

## 7. OR install as systemd service (production)
sudo cp itachi-bot.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable itachi-bot
sudo systemctl start itachi-bot

## 8. Check status
sudo systemctl status itachi-bot
sudo journalctl -u itachi-bot -f

# Docker Deployment (VPS)
# ================================

## 1. Install Docker
curl -fsSL https://get.docker.com | sh

## 2. Configure environment
cp .env.example .env
nano .env

## 3. Build and run
docker-compose up -d --build

## 4. Check logs
docker-compose logs -f bot

## 5. Restart
docker-compose restart bot

# Heroku Deployment
# ================================

## 1. Install Heroku CLI
curl https://cli-assets.heroku.com/install.sh | sh

## 2. Login
heroku login

## 3. Create app
heroku create itachi-bot

## 4. Set config vars
heroku config:set BOT_TOKEN=your_bot_token_here
heroku config:set MONGO_URI=your_mongo_uri_here

## 5. Deploy
git push heroku main

## 6. Check logs
heroku logs --tail

## 7. Keep alive (free tier sleeps after 30min)
heroku ps:scale web=1

# Railway Deployment
# ================================

## 1. Install Railway CLI
npm i -g @railway/cli

## 2. Login
railway login

## 3. Init project
railway init

## 4. Set variables
railway variables set BOT_TOKEN=your_bot_token_here
railway variables set MONGO_URI=your_mongo_uri_here

## 5. Deploy
railway up

## 6. Check logs
railway logs
