#!/usr/bin/env python3
"""
AI Content Platform - Deployment Setup Wizard
============================================

This wizard will help you deploy your AI Content Platform to the cloud.
Run this script and follow the prompts.

Usage:
    python setup-wizard.py

Requirements:
    - Python 3.8+
    - Git installed
    - Internet connection
"""

import os
import sys
import subprocess
import json
import secrets
import webbrowser
import time
from pathlib import Path

# Colors for terminal output
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    END = '\033[0m'
    BOLD = '\033[1m'

def print_header(text):
    print(f"\n{Colors.HEADER}{Colors.BOLD}{'='*60}{Colors.END}")
    print(f"{Colors.HEADER}{Colors.BOLD}{text.center(60)}{Colors.END}")
    print(f"{Colors.HEADER}{Colors.BOLD}{'='*60}{Colors.END}\n")

def print_step(num, text):
    print(f"\n{Colors.CYAN}{Colors.BOLD}Step {num}: {text}{Colors.END}")
    print(f"{Colors.CYAN}{'-'*50}{Colors.END}")

def print_success(text):
    print(f"{Colors.GREEN}✓ {text}{Colors.END}")

def print_warning(text):
    print(f"{Colors.YELLOW}⚠ {text}{Colors.END}")

def print_error(text):
    print(f"{Colors.RED}✗ {text}{Colors.END}")

def print_info(text):
    print(f"{Colors.BLUE}ℹ {text}{Colors.END}")

def ask(question, default=None):
    """Ask a question and return the answer."""
    if default:
        prompt = f"{question} [{default}]: "
    else:
        prompt = f"{question}: "
    
    answer = input(prompt).strip()
    return answer if answer else default

def ask_yes_no(question, default=True):
    """Ask a yes/no question."""
    default_str = "Y/n" if default else "y/N"
    answer = input(f"{question} [{default_str}]: ").strip().lower()
    
    if not answer:
        return default
    return answer in ('y', 'yes', 'true', '1')

def ask_secret(question):
    """Ask for a secret (API key, password, etc.)."""
    import getpass
    return getpass.getpass(f"{question}: ")

def open_browser(url):
    """Open a URL in the default browser."""
    print_info(f"Opening: {url}")
    webbrowser.open(url)
    input("Press Enter when you've completed this step...")

def check_command(cmd):
    """Check if a command is available."""
    try:
        subprocess.run([cmd, '--version'], capture_output=True, check=True)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False

def run_command(cmd, check=True, capture=False):
    """Run a shell command."""
    if capture:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        return result.stdout.strip()
    else:
        result = subprocess.run(cmd, shell=True)
        if check and result.returncode != 0:
            print_error(f"Command failed: {cmd}")
            sys.exit(1)
        return result.returncode == 0


class SetupWizard:
    def __init__(self):
        self.config = {
            'project_name': 'ai-content-platform',
            'env_vars': {}
        }
        self.project_dir = Path(__file__).parent
    
    def run(self):
        """Run the complete setup wizard."""
        print_header("AI Content Platform Setup Wizard")
        
        print("""
Welcome! This wizard will help you deploy your AI Content Platform.

We'll go through these steps:
  1. Check prerequisites (Git, etc.)
  2. Gather your API keys
  3. Set up GitHub repository
  4. Generate configuration files
  5. Deploy to Render

Let's get started!
        """)
        
        if not ask_yes_no("Ready to begin?"):
            print("Setup cancelled.")
            sys.exit(0)
        
        self.check_prerequisites()
        self.gather_api_keys()
        self.setup_github()
        self.generate_config_files()
        self.deploy_instructions()
        
        print_header("Setup Complete!")
        print("""
Your project is configured and ready for deployment!

Next steps:
1. Go to https://dashboard.render.com
2. Click "New" → "Blueprint"
3. Connect your GitHub repository
4. Select your repo and click "Apply"
5. Render will automatically deploy everything!

Your .env file has been created with all your API keys.
Your render.yaml blueprint is ready for one-click deployment.
        """)
    
    def check_prerequisites(self):
        """Check that required tools are installed."""
        print_step(1, "Checking Prerequisites")
        
        # Check Git
        if check_command('git'):
            print_success("Git is installed")
        else:
            print_error("Git is not installed")
            print_info("Please install Git from: https://git-scm.com/downloads")
            if sys.platform == 'darwin':
                print_info("Or run: brew install git")
            elif sys.platform == 'linux':
                print_info("Or run: sudo apt install git")
            sys.exit(1)
        
        # Check Python version
        if sys.version_info >= (3, 8):
            print_success(f"Python {sys.version_info.major}.{sys.version_info.minor} is installed")
        else:
            print_error("Python 3.8+ is required")
            sys.exit(1)
        
        # Check Node.js (optional but recommended)
        if check_command('node'):
            print_success("Node.js is installed")
        else:
            print_warning("Node.js is not installed (optional, needed for local frontend development)")
    
    def gather_api_keys(self):
        """Guide user through getting all required API keys."""
        print_step(2, "Gathering API Keys")
        
        print("""
You'll need API keys from several services. I'll open each website
for you and guide you through getting the keys.

Don't worry - this is a one-time setup!
        """)
        
        # Generate secret key
        self.config['env_vars']['SECRET_KEY'] = secrets.token_urlsafe(32)
        print_success("Generated SECRET_KEY automatically")
        
        # Admin account
        print(f"\n{Colors.BOLD}Admin Account Setup{Colors.END}")
        print("Set up your admin account to access the system after deployment.")
        
        admin_email = ask("Admin email address")
        if admin_email:
            self.config['env_vars']['ADMIN_EMAIL'] = admin_email
            admin_password = ask("Admin password (min 8 characters)")
            if admin_password:
                self.config['env_vars']['ADMIN_PASSWORD'] = admin_password
                print_success("Admin account configured - will be created on first deploy")
        
        # OpenAI
        print(f"\n{Colors.BOLD}OpenAI (Required - for text generation){Colors.END}")
        print("1. Sign up or log in to OpenAI")
        print("2. Go to API Keys section")
        print("3. Create a new secret key")
        if ask_yes_no("Open OpenAI website?"):
            open_browser("https://platform.openai.com/api-keys")
        
        openai_key = ask_secret("Paste your OpenAI API key")
        if openai_key:
            self.config['env_vars']['OPENAI_API_KEY'] = openai_key
            print_success("OpenAI API key saved")
        else:
            print_warning("Skipped - you'll need to add this later")
        
        # Replicate
        print(f"\n{Colors.BOLD}Replicate (Required - for image generation){Colors.END}")
        print("1. Sign up with GitHub or email")
        print("2. Go to Account → API Tokens")
        print("3. Copy your token")
        if ask_yes_no("Open Replicate website?"):
            open_browser("https://replicate.com/account/api-tokens")
        
        replicate_key = ask_secret("Paste your Replicate API token")
        if replicate_key:
            self.config['env_vars']['REPLICATE_API_TOKEN'] = replicate_key
            print_success("Replicate API token saved")
        else:
            print_warning("Skipped - you'll need to add this later")
        
        # Stripe
        print(f"\n{Colors.BOLD}Stripe (Required - for payments){Colors.END}")
        print("1. Sign up for Stripe")
        print("2. Go to Developers → API Keys (stay in Test Mode for now)")
        print("3. Copy both Publishable and Secret keys")
        if ask_yes_no("Open Stripe website?"):
            open_browser("https://dashboard.stripe.com/test/apikeys")
        
        stripe_pk = ask("Paste your Stripe Publishable key (pk_test_...)")
        stripe_sk = ask_secret("Paste your Stripe Secret key (sk_test_...)")
        
        if stripe_pk and stripe_sk:
            self.config['env_vars']['STRIPE_PUBLISHABLE_KEY'] = stripe_pk
            self.config['env_vars']['STRIPE_SECRET_KEY'] = stripe_sk
            print_success("Stripe keys saved")
            
            print(f"\n{Colors.BOLD}Now let's create your Stripe products:{Colors.END}")
            print("You need to create 3 subscription products in Stripe.")
            if ask_yes_no("Open Stripe Products page?"):
                open_browser("https://dashboard.stripe.com/test/products")
            
            print("""
Create these products:
  1. Creator Plan - $19/month (recurring)
  2. Pro Plan - $49/month (recurring)  
  3. Agency Plan - $149/month (recurring)

After creating each, click on it and copy the Price ID (starts with price_)
            """)
            
            creator_price = ask("Creator Plan Price ID (price_...)")
            pro_price = ask("Pro Plan Price ID (price_...)")
            agency_price = ask("Agency Plan Price ID (price_...)")
            
            if creator_price:
                self.config['env_vars']['STRIPE_CREATOR_PRICE_ID'] = creator_price
            if pro_price:
                self.config['env_vars']['STRIPE_PRO_PRICE_ID'] = pro_price
            if agency_price:
                self.config['env_vars']['STRIPE_AGENCY_PRICE_ID'] = agency_price
        else:
            print_warning("Skipped Stripe - you'll need to add this later")
        
        # Resend
        print(f"\n{Colors.BOLD}Resend (Required - for emails){Colors.END}")
        print("1. Sign up at Resend")
        print("2. Create an API key")
        if ask_yes_no("Open Resend website?"):
            open_browser("https://resend.com/api-keys")
        
        resend_key = ask_secret("Paste your Resend API key")
        if resend_key:
            self.config['env_vars']['RESEND_API_KEY'] = resend_key
            print_success("Resend API key saved")
        else:
            print_warning("Skipped - you'll need to add this later")
        
        # ElevenLabs (optional)
        print(f"\n{Colors.BOLD}ElevenLabs (Optional - for video voice generation){Colors.END}")
        if ask_yes_no("Do you want to set up ElevenLabs for voice generation?", default=False):
            if ask_yes_no("Open ElevenLabs website?"):
                open_browser("https://elevenlabs.io/")
            
            eleven_key = ask_secret("Paste your ElevenLabs API key")
            if eleven_key:
                self.config['env_vars']['ELEVENLABS_API_KEY'] = eleven_key
                print_success("ElevenLabs API key saved")
        
        # Email settings
        print(f"\n{Colors.BOLD}Email Settings{Colors.END}")
        email_from = ask("From email address for notifications", "noreply@example.com")
        self.config['env_vars']['EMAIL_FROM'] = email_from
    
    def setup_github(self):
        """Set up Git and GitHub repository."""
        print_step(3, "Setting Up GitHub Repository")
        
        # Check if already a git repo
        if (self.project_dir / '.git').exists():
            print_success("Git repository already initialized")
        else:
            print_info("Initializing Git repository...")
            os.chdir(self.project_dir)
            run_command("git init")
            print_success("Git repository initialized")
        
        # Check for existing remote
        result = run_command("git remote -v", capture=True, check=False)
        if 'origin' in result:
            print_success("GitHub remote already configured")
            self.config['github_url'] = result.split()[1] if result else ''
        else:
            print("""
Now we need to create a GitHub repository.
            """)
            
            if ask_yes_no("Do you have the GitHub CLI (gh) installed?", default=False):
                # Use GitHub CLI
                repo_name = ask("Repository name", "ai-content-platform")
                private = ask_yes_no("Make repository private?", default=False)
                
                visibility = "--private" if private else "--public"
                run_command(f'gh repo create {repo_name} {visibility} --source=. --remote=origin --push')
                print_success("GitHub repository created and code pushed!")
            else:
                # Manual instructions
                print("""
Let's create the GitHub repository manually:

1. Go to https://github.com/new
2. Repository name: ai-content-platform
3. Choose Public or Private
4. DON'T initialize with README (we already have code)
5. Click "Create repository"
6. Copy the repository URL
                """)
                
                if ask_yes_no("Open GitHub?"):
                    open_browser("https://github.com/new")
                
                repo_url = ask("Paste your GitHub repository URL (https://github.com/...)")
                
                if repo_url:
                    os.chdir(self.project_dir)
                    run_command(f'git remote add origin {repo_url}')
                    run_command('git add .')
                    run_command('git commit -m "Initial commit - AI Content Platform"', check=False)
                    
                    print_info("Pushing code to GitHub...")
                    if run_command('git push -u origin main', check=False):
                        print_success("Code pushed to GitHub!")
                    else:
                        # Try with master branch
                        run_command('git branch -M main', check=False)
                        run_command('git push -u origin main', check=False)
                    
                    self.config['github_url'] = repo_url
    
    def generate_config_files(self):
        """Generate all configuration files."""
        print_step(4, "Generating Configuration Files")
        
        # Generate .env file
        self.generate_env_file()
        
        # Generate render.yaml
        self.generate_render_yaml()
        
        # Update .gitignore
        self.update_gitignore()
        
        print_success("All configuration files generated!")
    
    def generate_env_file(self):
        """Generate .env file with all API keys."""
        env_content = """# AI Content Platform Environment Variables
# Generated by setup wizard

# ===========================================
# REQUIRED SETTINGS
# ===========================================

# Security
SECRET_KEY={SECRET_KEY}

# Database (will be set by Render)
DATABASE_URL=

# Redis (will be set by Render)
REDIS_URL=

# ===========================================
# ADMIN ACCESS
# ===========================================
# Your admin account - created automatically on first deploy
# Access the admin dashboard at /admin after logging in
ADMIN_EMAIL={ADMIN_EMAIL}
ADMIN_PASSWORD={ADMIN_PASSWORD}

# OpenAI - Text Generation
OPENAI_API_KEY={OPENAI_API_KEY}

# Replicate - Image Generation
REPLICATE_API_TOKEN={REPLICATE_API_TOKEN}

# ===========================================
# STRIPE PAYMENTS
# ===========================================
STRIPE_SECRET_KEY={STRIPE_SECRET_KEY}
STRIPE_PUBLISHABLE_KEY={STRIPE_PUBLISHABLE_KEY}
STRIPE_WEBHOOK_SECRET=

# Stripe Price IDs (create products in Stripe Dashboard)
STRIPE_CREATOR_PRICE_ID={STRIPE_CREATOR_PRICE_ID}
STRIPE_PRO_PRICE_ID={STRIPE_PRO_PRICE_ID}
STRIPE_AGENCY_PRICE_ID={STRIPE_AGENCY_PRICE_ID}

# ===========================================
# EMAIL
# ===========================================
RESEND_API_KEY={RESEND_API_KEY}
EMAIL_FROM={EMAIL_FROM}

# ===========================================
# OPTIONAL SERVICES
# ===========================================

# ElevenLabs - Voice Generation
ELEVENLABS_API_KEY={ELEVENLABS_API_KEY}

# Frontend URL (update after deployment)
FRONTEND_URL=http://localhost:5173

# ===========================================
# SOCIAL MEDIA (Optional - for social posting)
# ===========================================
# TWITTER_CLIENT_ID=
# TWITTER_CLIENT_SECRET=
# INSTAGRAM_CLIENT_ID=
# INSTAGRAM_CLIENT_SECRET=
# LINKEDIN_CLIENT_ID=
# LINKEDIN_CLIENT_SECRET=
"""
        
        # Fill in values
        for key, value in self.config['env_vars'].items():
            env_content = env_content.replace(f'{{{key}}}', value or '')
        
        # Remove unfilled placeholders
        import re
        env_content = re.sub(r'\{[A-Z_]+\}', '', env_content)
        
        env_path = self.project_dir / '.env'
        with open(env_path, 'w') as f:
            f.write(env_content)
        
        print_success(f"Created .env file")
    
    def generate_render_yaml(self):
        """Generate render.yaml for one-click deployment."""
        render_yaml = """# Render Blueprint - AI Content Platform
# This file enables one-click deployment to Render

services:
  # Backend API
  - type: web
    name: ai-content-platform-api
    runtime: python
    buildCommand: pip install -r requirements.txt
    startCommand: uvicorn app.main:app --host 0.0.0.0 --port $PORT
    healthCheckPath: /health
    envVars:
      - key: DATABASE_URL
        fromDatabase:
          name: ai-content-platform-db
          property: connectionString
      - key: REDIS_URL
        fromService:
          name: ai-content-platform-redis
          type: redis
          property: connectionString
      - key: SECRET_KEY
        generateValue: true
      - key: OPENAI_API_KEY
        sync: false
      - key: REPLICATE_API_TOKEN
        sync: false
      - key: STRIPE_SECRET_KEY
        sync: false
      - key: STRIPE_PUBLISHABLE_KEY
        sync: false
      - key: STRIPE_WEBHOOK_SECRET
        sync: false
      - key: STRIPE_CREATOR_PRICE_ID
        sync: false
      - key: STRIPE_PRO_PRICE_ID
        sync: false
      - key: STRIPE_AGENCY_PRICE_ID
        sync: false
      - key: RESEND_API_KEY
        sync: false
      - key: EMAIL_FROM
        sync: false
      - key: ELEVENLABS_API_KEY
        sync: false
      - key: FRONTEND_URL
        sync: false

  # Background Worker (for async tasks)
  - type: worker
    name: ai-content-platform-worker
    runtime: python
    buildCommand: pip install -r requirements.txt
    startCommand: celery -A app.worker worker --loglevel=info
    envVars:
      - key: DATABASE_URL
        fromDatabase:
          name: ai-content-platform-db
          property: connectionString
      - key: REDIS_URL
        fromService:
          name: ai-content-platform-redis
          type: redis
          property: connectionString
      - key: SECRET_KEY
        generateValue: true
      - key: OPENAI_API_KEY
        sync: false
      - key: REPLICATE_API_TOKEN
        sync: false
      - key: ELEVENLABS_API_KEY
        sync: false

  # Frontend
  - type: web
    name: ai-content-platform
    runtime: static
    buildCommand: cd frontend && npm install && npm run build
    staticPublishPath: frontend/dist
    headers:
      - path: /*
        name: Cache-Control
        value: public, max-age=0, must-revalidate
    routes:
      - type: rewrite
        source: /*
        destination: /index.html
    envVars:
      - key: VITE_API_URL
        value: https://ai-content-platform-api.onrender.com/api/v1

  # Redis
  - type: redis
    name: ai-content-platform-redis
    plan: free
    maxmemoryPolicy: allkeys-lru

databases:
  - name: ai-content-platform-db
    plan: free
    databaseName: aiplatform
    user: aiplatform
"""
        
        render_path = self.project_dir / 'render.yaml'
        with open(render_path, 'w') as f:
            f.write(render_yaml)
        
        print_success("Created render.yaml (Render blueprint)")
    
    def update_gitignore(self):
        """Ensure .env is in .gitignore."""
        gitignore_path = self.project_dir / '.gitignore'
        
        gitignore_content = ""
        if gitignore_path.exists():
            with open(gitignore_path, 'r') as f:
                gitignore_content = f.read()
        
        additions = []
        if '.env' not in gitignore_content:
            additions.append('.env')
        if '.env.local' not in gitignore_content:
            additions.append('.env.local')
        if '*.pyc' not in gitignore_content:
            additions.append('*.pyc')
        if '__pycache__' not in gitignore_content:
            additions.append('__pycache__/')
        if 'node_modules' not in gitignore_content:
            additions.append('node_modules/')
        
        if additions:
            with open(gitignore_path, 'a') as f:
                f.write('\n# Added by setup wizard\n')
                for item in additions:
                    f.write(f'{item}\n')
            print_success("Updated .gitignore")
    
    def deploy_instructions(self):
        """Show final deployment instructions."""
        print_step(5, "Deploy to Render")
        
        print(f"""
{Colors.GREEN}{Colors.BOLD}Your project is ready for deployment!{Colors.END}

{Colors.BOLD}Option A: One-Click Deploy (Recommended){Colors.END}
{'-'*40}
1. Go to: https://dashboard.render.com
2. Click "New" → "Blueprint"  
3. Connect your GitHub account (if not already connected)
4. Select your repository: {self.config.get('github_url', 'ai-content-platform')}
5. Render will detect your render.yaml automatically
6. Click "Apply" to deploy everything!

{Colors.BOLD}After deployment:{Colors.END}
{'-'*40}
1. Go to your API service in Render
2. Click "Environment" tab
3. Add your API keys (the ones marked 'sync: false'):
   - OPENAI_API_KEY
   - REPLICATE_API_TOKEN
   - STRIPE_SECRET_KEY
   - STRIPE_PUBLISHABLE_KEY
   - RESEND_API_KEY
   - etc.

4. Run database migrations:
   - Go to your API service
   - Click "Shell" tab
   - Run: alembic upgrade head

5. Set up Stripe webhook:
   - Go to Stripe Dashboard → Developers → Webhooks
   - Add endpoint: https://ai-content-platform-api.onrender.com/api/v1/billing/webhook
   - Copy the webhook secret
   - Add it as STRIPE_WEBHOOK_SECRET in Render

{Colors.BOLD}Your URLs will be:{Colors.END}
{'-'*40}
Frontend: https://ai-content-platform.onrender.com
API:      https://ai-content-platform-api.onrender.com
API Docs: https://ai-content-platform-api.onrender.com/docs
        """)
        
        if ask_yes_no("Open Render dashboard now?"):
            open_browser("https://dashboard.render.com/select-repo?type=blueprint")


def main():
    """Main entry point."""
    try:
        wizard = SetupWizard()
        wizard.run()
    except KeyboardInterrupt:
        print("\n\nSetup cancelled by user.")
        sys.exit(1)
    except Exception as e:
        print_error(f"An error occurred: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
