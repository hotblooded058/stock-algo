# Deploy to Streamlit Community Cloud (Free)

Your dashboard will be live at a URL like: `https://your-app-name.streamlit.app`
Accessible from phone, tablet, or any browser — anywhere.

## Step-by-step

### 1. Create a GitHub account (if you don't have one)
Go to https://github.com and sign up. It's free.

### 2. Push your project to GitHub

Open Terminal and run these commands one by one:

```bash
cd ~/Stock-algo

# Initialize git
git init
git add .
git commit -m "Initial commit: Options Trading Platform"

# Create repo on GitHub (you need GitHub CLI — install with: brew install gh)
gh auth login
gh repo create stock-algo --public --source=. --push
```

If you don't want to use `gh` CLI, you can also:
1. Go to https://github.com/new
2. Create a new repo called `stock-algo`
3. Follow the instructions GitHub shows to push existing code

### 3. Deploy on Streamlit Cloud

1. Go to https://share.streamlit.io
2. Sign in with your GitHub account
3. Click **"New app"**
4. Select your repo: `stock-algo`
5. Set **Main file path** to: `dashboard.py`
6. Click **"Deploy"**

That's it! In about 2 minutes your app will be live.

### 4. Access from phone

Once deployed, you'll get a URL like:
```
https://sachin-stock-algo.streamlit.app
```

Open this on your phone browser, add it to your home screen, and it works like an app.

## Notes

- **Free tier limits:** Streamlit Cloud free tier sleeps after 7 days of inactivity. Just visit the URL to wake it up.
- **Updates:** Every time you push to GitHub, the app auto-redeploys.
- **Secrets:** Never push API keys to GitHub. Use Streamlit's Secrets management instead (Settings → Secrets in the Streamlit Cloud dashboard).

## Updating your app after deployment

```bash
cd ~/Stock-algo
git add .
git commit -m "Update: description of what changed"
git push
```
The app will automatically redeploy within a minute.
