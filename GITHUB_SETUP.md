# GitHub Setup Guide - FNAC

This guide helps you push FNAC to GitHub and pull it on your Astra Linux server.

## Step 1: Create a GitHub Repository

1. Go to https://github.com/new
2. Create a new repository named `fnac`
3. Choose "Public" or "Private" (your preference)
4. Do NOT initialize with README (we already have one)
5. Click "Create repository"

## Step 2: Push to GitHub (from your development machine)

```bash
# Navigate to your project directory
cd /path/to/fnac

# Initialize git (if not already done)
git init

# Add all files
git add .

# Commit
git commit -m "Initial commit: FNAC - RADIUS server with web UI"

# Add remote (replace USERNAME with your GitHub username)
git remote add origin https://github.com/USERNAME/fnac.git

# Push to GitHub
git branch -M main
git push -u origin main
```

## Step 3: Pull on Your Astra Linux Server

```bash
# SSH into your Astra Linux server
ssh user@your-server

# Navigate to where you want to install it
cd /home/localadmin

# Clone the repository
git clone https://github.com/USERNAME/fnac.git

# Navigate into the directory
cd fnac

# Setup and run
./quickstart.sh setup
sudo -E ./quickstart.sh run
```

## Step 4: Access the Web UI

Open your browser and go to:
```
http://your-server-ip:5000
```

## Updating Your Server

When you make changes on your development machine:

```bash
# On your development machine
git add .
git commit -m "Your commit message"
git push origin main

# On your Astra Linux server
cd /home/localadmin/fnac
git pull origin main

# Restart the server
./quickstart.sh stop
sudo -E ./quickstart.sh run
```

## Using SSH Keys (Recommended for Production)

Instead of using HTTPS with passwords, use SSH keys:

### Generate SSH key on your server:
```bash
ssh-keygen -t rsa -b 4096 -f ~/.ssh/id_rsa
cat ~/.ssh/id_rsa.pub
```

### Add the public key to GitHub:
1. Go to GitHub Settings → SSH and GPG keys
2. Click "New SSH key"
3. Paste the content of `~/.ssh/id_rsa.pub`
4. Click "Add SSH key"

### Clone using SSH:
```bash
git clone git@github.com:USERNAME/fnac.git
```

## Troubleshooting

### "Permission denied (publickey)"
Make sure your SSH key is added to GitHub and the permissions are correct:
```bash
chmod 600 ~/.ssh/id_rsa
chmod 644 ~/.ssh/id_rsa.pub
```

### "fatal: not a git repository"
Make sure you're in the correct directory:
```bash
cd /path/to/fnac
git status
```

### "Your branch is ahead of 'origin/main'"
Push your changes:
```bash
git push origin main
```

## GitHub Repository Structure

Your repository will have:
```
fnac/
├── src/                    # Python source code
│   ├── static/            # Web UI files
│   │   ├── index.html
│   │   ├── style.css
│   │   └── app.js
│   ├── main.py
│   ├── api.py
│   ├── models.py
│   ├── persistence.py
│   ├── device_manager.py
│   ├── client_manager.py
│   ├── policy_engine.py
│   ├── log_manager.py
│   ├── radius_server.py
│   └── ...
├── tests/                 # Test files
├── requirements.txt       # Python dependencies
├── quickstart.sh         # Setup script
├── README.md             # Documentation
├── .gitignore            # Git ignore rules
└── ...
```

## Continuous Deployment (Optional)

For automatic deployment when you push to GitHub, consider using:
- GitHub Actions
- Webhooks
- CI/CD pipelines

This is beyond the scope of this guide but can be set up for production environments.

## Security Notes

1. Never commit sensitive data (passwords, API keys, etc.)
2. Use `.gitignore` to exclude data files
3. Use SSH keys instead of HTTPS passwords
4. Keep your repository private if it contains sensitive configuration
5. Regularly update dependencies: `pip install --upgrade -r requirements.txt`

## Support

For more information on Git and GitHub:
- Git documentation: https://git-scm.com/doc
- GitHub documentation: https://docs.github.com
- GitHub SSH setup: https://docs.github.com/en/authentication/connecting-to-github-with-ssh
