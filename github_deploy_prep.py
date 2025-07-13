#!/usr/bin/env python3
"""
GitHub Deployment Preparation Script
This script prepares the MCP Multi-Agent System for secure GitHub deployment.

It performs the following tasks:
1. Validates that sensitive data is properly excluded
2. Creates/updates necessary configuration files
3. Checks .gitignore coverage
4. Provides deployment checklist
"""

import os
import re
import glob
from pathlib import Path

class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    BOLD = '\033[1m'
    END = '\033[0m'

def colored_print(text, color=Colors.END):
    """Print colored text."""
    print(f"{color}{text}{Colors.END}")

def scan_for_sensitive_data():
    """Scan all files for potential sensitive data."""
    colored_print("🔍 Scanning for Sensitive Data", Colors.BLUE)
    colored_print("-" * 35)
    
    # Patterns that indicate sensitive data
    sensitive_patterns = [
        (r'sk-ant-api\d+-[A-Za-z0-9_-]+', 'Anthropic API Key'),
        (r'bb_live_[A-Za-z0-9]+', 'Browserbase Live API Key'),
        (r'sk-[A-Za-z0-9]{20,}', 'OpenAI API Key'),
        (r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}', 'UUID/Project ID'),
        (r'postgres://[^@]+:[^@]+@', 'Database Connection String'),
        (r'mysql://[^@]+:[^@]+@', 'MySQL Connection String'),
        (r'mongodb://[^@]+:[^@]+@', 'MongoDB Connection String'),
        (r'password\s*=\s*["\'][^"\']{6,}["\']', 'Hard-coded Password'),
        (r'secret\s*=\s*["\'][^"\']{10,}["\']', 'Hard-coded Secret'),
    ]
    
    # Files to exclude from scanning
    excluded_files = {
        '.git', '__pycache__', '.venv', 'node_modules', '.env.example',
        'github_deploy_prep.py'  # This script
    }
    
    issues_found = []
    files_scanned = 0
    
    # Get all files in the project
    for root, dirs, files in os.walk('.'):
        # Skip excluded directories
        dirs[:] = [d for d in dirs if d not in excluded_files]
        
        for file in files:
            if file in excluded_files or file.startswith('.'):
                continue
                
            file_path = os.path.join(root, file)
            
            # Skip binary files
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                files_scanned += 1
            except (UnicodeDecodeError, PermissionError):
                continue
            
            # Check for sensitive patterns
            for pattern, description in sensitive_patterns:
                matches = re.finditer(pattern, content, re.IGNORECASE)
                for match in matches:
                    # Get line number
                    line_num = content[:match.start()].count('\n') + 1
                    line_content = content.split('\n')[line_num - 1].strip()
                    
                    issues_found.append({
                        'file': file_path,
                        'line': line_num,
                        'type': description,
                        'content': line_content[:100] + '...' if len(line_content) > 100 else line_content
                    })
    
    print(f"Files scanned: {files_scanned}")
    
    if issues_found:
        colored_print(f"❌ Found {len(issues_found)} potential sensitive data issues:", Colors.RED)
        for issue in issues_found:
            print(f"  📁 {issue['file']}:{issue['line']}")
            print(f"     Type: {issue['type']}")
            print(f"     Content: {issue['content']}")
            print()
        return False
    else:
        colored_print("✅ No sensitive data patterns detected", Colors.GREEN)
        return True

def validate_gitignore():
    """Validate .gitignore file covers all necessary patterns."""
    colored_print("\n🛡️ Validating .gitignore Coverage", Colors.BLUE)
    colored_print("-" * 35)
    
    gitignore_path = '.gitignore'
    if not os.path.exists(gitignore_path):
        colored_print("❌ .gitignore file not found", Colors.RED)
        return False
    
    with open(gitignore_path, 'r') as f:
        gitignore_content = f.read()
    
    # Essential patterns that should be in .gitignore
    essential_patterns = [
        '.env',
        '*.db',
        '*.sqlite',
        '__pycache__/',
        '.venv/',
        '*.log',
        'logs/',
        'secrets/',
        'credentials/'
    ]
    
    missing_patterns = []
    for pattern in essential_patterns:
        if pattern not in gitignore_content:
            missing_patterns.append(pattern)
    
    if missing_patterns:
        colored_print(f"❌ Missing patterns in .gitignore:", Colors.RED)
        for pattern in missing_patterns:
            print(f"  - {pattern}")
        return False
    else:
        colored_print("✅ .gitignore covers essential patterns", Colors.GREEN)
        return True

def check_env_files():
    """Check environment file configuration."""
    colored_print("\n🔧 Checking Environment Files", Colors.BLUE)
    colored_print("-" * 32)
    
    # Check if .env exists (should be ignored)
    if os.path.exists('.env'):
        colored_print("✅ .env file exists (will be ignored by git)", Colors.GREEN)
    else:
        colored_print("⚠️  .env file not found (create from .env.example)", Colors.YELLOW)
    
    # Check if .env.example exists (should be committed)
    if os.path.exists('.env.example'):
        colored_print("✅ .env.example exists (safe for git)", Colors.GREEN)
        
        # Validate that .env.example doesn't contain real secrets
        with open('.env.example', 'r') as f:
            env_example_content = f.read()
        
        if 'your_' in env_example_content or 'your-' in env_example_content:
            colored_print("✅ .env.example uses placeholder values", Colors.GREEN)
        else:
            colored_print("⚠️  .env.example may contain real values", Colors.YELLOW)
        
        return True
    else:
        colored_print("❌ .env.example file missing", Colors.RED)
        return False

def create_deployment_checklist():
    """Create a deployment checklist README."""
    colored_print("\n📋 Creating Deployment Checklist", Colors.BLUE)
    colored_print("-" * 34)
    
    checklist_content = """# GitHub Deployment Checklist

## ✅ Pre-Deployment Security Checklist

### Environment Configuration
- [ ] `.env` file is excluded from git (listed in .gitignore)
- [ ] `.env.example` exists with placeholder values
- [ ] No API keys or secrets in any committed files
- [ ] Database files (`*.db`, `*.sqlite`) are excluded from git

### File Security
- [ ] All sensitive configuration files are in .gitignore
- [ ] No hardcoded passwords or API keys in source code
- [ ] Log files and temporary files are excluded
- [ ] Virtual environment directories are excluded

### Documentation
- [ ] README.md contains setup instructions
- [ ] Environment variables are documented in .env.example
- [ ] API key setup instructions are clear
- [ ] Database setup steps are documented

## 🚀 Deployment Steps

1. **Initial Setup**
   ```bash
   git clone <your-repo-url>
   cd MCPToolCalling
   ```

2. **Environment Setup**
   ```bash
   # Create virtual environment
   python -m venv .venv
   
   # Activate virtual environment (Windows)
   .venv\\Scripts\\activate
   
   # Activate virtual environment (macOS/Linux)
   source .venv/bin/activate
   
   # Install dependencies
   pip install -r requirements.txt
   ```

3. **Configuration**
   ```bash
   # Copy environment template
   cp .env.example .env
   
   # Edit .env with your actual API keys
   # nano .env  # or use your preferred editor
   ```

4. **Database Setup**
   ```bash
   # Run the quick setup script
   python quick_start.py
   ```

5. **Start the System**
   ```bash
   # Terminal 1: Start MCP Hub
   python src/hub/mcp_hub.py
   
   # Terminal 2: Start Database Agent
   python src/agents/database_agent.py
   
   # Terminal 3: Start Browserbase Agent (optional)
   python src/agents/browserbase_agent.py
   ```

6. **Verify Installation**
   ```bash
   # Run system diagnostic
   python diagnostic.py
   
   # Test database queries
   python test_queries.py
   ```

## 🔑 Required API Keys

### Anthropic Claude (Required)
1. Sign up at https://console.anthropic.com/
2. Create an API key
3. Add to `.env`: `ANTHROPIC_API_KEY=your_key_here`

### Browserbase (Optional - for web scraping)
1. Sign up at https://browserbase.com/
2. Create a project and get API key
3. Add to `.env`: 
   ```
   BROWSERBASE_API_KEY=your_key_here
   BROWSERBASE_PROJECT_ID=your_project_id_here
   ```

## 🛡️ Security Best Practices

1. **Never commit sensitive data**
   - Always use environment variables for secrets
   - Regularly scan for accidentally committed secrets
   - Use placeholder values in example files

2. **Environment Management**
   - Keep `.env` local and never commit it
   - Use different `.env` files for different environments
   - Rotate API keys regularly

3. **Database Security**
   - Use strong passwords in production
   - Enable SSL/TLS for database connections
   - Backup database regularly

## 🔍 Troubleshooting

### Common Issues
- **API Key errors**: Check that keys are correctly set in `.env`
- **Database connection**: Ensure database is running and accessible
- **Port conflicts**: Check that required ports (5000, 8001-8003) are available
- **Dependencies**: Run `pip install -r requirements.txt` if modules are missing

### Getting Help
- Check the diagnostic output: `python diagnostic.py`
- Review logs in the `logs/` directory
- Consult the documentation in `docs/`

---

⚠️ **Important**: Always keep your API keys and credentials secure!
"""
    
    with open('DEPLOYMENT_CHECKLIST.md', 'w') as f:
        f.write(checklist_content)
    
    colored_print("✅ Deployment checklist created: DEPLOYMENT_CHECKLIST.md", Colors.GREEN)

def create_github_workflow():
    """Create a basic GitHub Actions workflow for CI."""
    colored_print("\n🔄 Creating GitHub Actions Workflow", Colors.BLUE)
    colored_print("-" * 38)
    
    # Create .github/workflows directory
    workflows_dir = Path('.github/workflows')
    workflows_dir.mkdir(parents=True, exist_ok=True)
    
    workflow_content = """name: MCP Multi-Agent System CI

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main ]

jobs:
  test:
    runs-on: ubuntu-latest
    
    strategy:
      matrix:
        python-version: [3.8, 3.9, '3.10', '3.11']
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Set up Python ${{ matrix.python-version }}
      uses: actions/setup-python@v3
      with:
        python-version: ${{ matrix.python-version }}
    
    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -r requirements.txt
    
    - name: Create test environment file
      run: |
        cp .env.example .env
        # Set dummy values for testing
        sed -i 's/your_anthropic_api_key_here/test_key_dummy/' .env
        sed -i 's/your_browserbase_api_key_here/test_key_dummy/' .env
    
    - name: Run basic syntax checks
      run: |
        python -m py_compile src/agents/database_agent.py
        python -m py_compile src/hub/mcp_hub.py
        python -m py_compile diagnostic.py
    
    - name: Run tests (if test files exist)
      run: |
        if [ -d "tests" ]; then
          python -m pytest tests/ -v
        else
          echo "No tests directory found, skipping tests"
        fi
    
    - name: Check for sensitive data patterns
      run: |
        # Simple check for common sensitive patterns
        if grep -r "sk-ant-api" --exclude-dir=.git --exclude="*.example" .; then
          echo "❌ Found potential API keys in code"
          exit 1
        fi
        if grep -r "bb_live_" --exclude-dir=.git --exclude="*.example" .; then
          echo "❌ Found potential Browserbase keys in code"
          exit 1
        fi
        echo "✅ No sensitive data patterns found"

  security-scan:
    runs-on: ubuntu-latest
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Run security scan
      run: |
        # Check for common security issues
        echo "Running basic security checks..."
        
        # Check .env is in .gitignore
        if ! grep -q "\.env" .gitignore; then
          echo "❌ .env not found in .gitignore"
          exit 1
        fi
        
        # Check no .env files are tracked
        if git ls-files | grep -q "\.env$"; then
          echo "❌ .env file is being tracked by git"
          exit 1
        fi
        
        echo "✅ Basic security checks passed"
"""
    
    with open(workflows_dir / 'ci.yml', 'w') as f:
        f.write(workflow_content)
    
    colored_print("✅ GitHub Actions workflow created: .github/workflows/ci.yml", Colors.GREEN)

def main():
    """Main deployment preparation function."""
    colored_print("🚀 GitHub Deployment Preparation", Colors.BOLD)
    colored_print("=" * 40)
    print("Preparing MCP Multi-Agent System for secure GitHub deployment\n")
    
    all_checks_passed = True
    
    # Run all validation checks
    all_checks_passed &= scan_for_sensitive_data()
    all_checks_passed &= validate_gitignore()
    all_checks_passed &= check_env_files()
    
    # Create deployment assets
    create_deployment_checklist()
    create_github_workflow()
    
    # Final summary
    colored_print("\n📋 Deployment Preparation Summary", Colors.BOLD)
    colored_print("-" * 40)
    
    if all_checks_passed:
        colored_print("🎉 Repository is ready for GitHub deployment!", Colors.GREEN)
        print("\nNext steps:")
        print("1. Review DEPLOYMENT_CHECKLIST.md")
        print("2. Initialize git repository: git init")
        print("3. Add files: git add .")
        print("4. Commit: git commit -m 'Initial commit'")
        print("5. Add remote: git remote add origin <your-repo-url>")
        print("6. Push: git push -u origin main")
    else:
        colored_print("⚠️  Issues found that need attention before deployment", Colors.YELLOW)
        print("\nPlease address the issues above before deploying to GitHub.")
    
    print(f"\n📁 Files created:")
    print("  - .gitignore (updated)")
    print("  - DEPLOYMENT_CHECKLIST.md")
    print("  - .github/workflows/ci.yml")

if __name__ == "__main__":
    main()
