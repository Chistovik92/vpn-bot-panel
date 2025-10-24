#!/bin/bash

# VPN Bot Panel Installation Script
set -e  # Exit on any error

echo "🚀 Starting VPN Bot Panel installation..."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${BLUE}ℹ️ $1${NC}"
}

log_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

log_warning() {
    echo -e "${YELLOW}⚠️ $1${NC}"
}

log_error() {
    echo -e "${RED}❌ $1${NC}"
}

# Check if running as root
check_root() {
    if [[ $EUID -eq 0 ]]; then
        log_warning "Running as root user. It's recommended to run as regular user."
        read -p "Continue as root? (y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            log_info "Exiting. Please run as regular user."
            exit 1
        fi
    fi
}

# Check if Git is installed
check_git() {
    if ! command -v git &>/dev/null; then
        log_error "Git is not installed. Please install git first:"
        log_info "Ubuntu/Debian: sudo apt-get install git"
        log_info "CentOS/RHEL: sudo yum install git"
        log_info "macOS: brew install git"
        exit 1
    fi
    log_success "Git found: $(git --version)"
}

# Clone or update repository
setup_repository() {
    local repo_url="https://github.com/Chistovik92/vpn-bot-panel.git"
    local project_dir="vpn-bot-panel"
    
    if [ -d "$project_dir" ]; then
        log_info "Project directory already exists, updating..."
        cd "$project_dir"
        git pull origin main
        log_success "Repository updated"
    else
        log_info "Cloning repository from $repo_url..."
        git clone "$repo_url" "$project_dir"
        cd "$project_dir"
        log_success "Repository cloned successfully"
    fi
    
    # Show current directory and files
    log_info "Current directory: $(pwd)"
    log_info "Files in directory:"
    ls -la
}

# Check if Python is installed
check_python() {
    log_info "Checking Python installation..."
    if command -v python3 &>/dev/null; then
        PYTHON_CMD="python3"
        log_success "Python 3 found: $(python3 --version)"
    elif command -v python &>/dev/null; then
        PYTHON_VERSION=$(python --version 2>&1)
        if [[ $PYTHON_VERSION == *"Python 3"* ]]; then
            PYTHON_CMD="python"
            log_success "Python found: $PYTHON_VERSION"
        else
            log_error "Python 3 is required but not found. Please install Python 3.8 or higher."
            exit 1
        fi
    else
        log_error "Python is not installed. Please install Python 3.8 or higher."
        exit 1
    fi
}

# Check Python version
check_python_version() {
    log_info "Checking Python version..."
    PYTHON_VERSION=$($PYTHON_CMD -c "import sys; print('.'.join(map(str, sys.version_info[:3])))")
    REQUIRED_VERSION="3.8"
    
    $PYTHON_CMD -c "import sys; exit(0) if tuple(map(int, sys.version_info[:2])) >= tuple(map(int, '$REQUIRED_VERSION'.split('.'))) else exit(1)"
    
    if [ $? -eq 0 ]; then
        log_success "Python version $PYTHON_VERSION is compatible"
    else
        log_error "Python $REQUIRED_VERSION or higher is required. Current version: $PYTHON_VERSION"
        exit 1
    fi
}

# Check if required files exist
check_required_files() {
    log_info "Checking required files..."
    
    local required_files=("install.py" "database.py" "config.py" "requirements.txt")
    local missing_files=()
    
    for file in "${required_files[@]}"; do
        if [ ! -f "$file" ]; then
            missing_files+=("$file")
        fi
    done
    
    if [ ${#missing_files[@]} -ne 0 ]; then
        log_error "Missing required files: ${missing_files[*]}"
        return 1
    fi
    
    log_success "All required files found"
    return 0
}

# Create virtual environment
create_venv() {
    log_info "Creating Python virtual environment..."
    
    if [ ! -d "venv" ]; then
        $PYTHON_CMD -m venv venv
        log_success "Virtual environment created"
    else
        log_info "Virtual environment already exists"
    fi
}

# Activate virtual environment and get Python path
activate_venv() {
    if [ -f "venv/bin/activate" ]; then
        source venv/bin/activate
        PYTHON_CMD="venv/bin/python"
        log_success "Virtual environment activated"
    elif [ -f "venv/Scripts/activate" ]; then
        source venv/Scripts/activate
        PYTHON_CMD="venv/Scripts/python"
        log_success "Virtual environment activated"
    else
        log_warning "Could not activate virtual environment, using system Python"
    fi
}

# Install dependencies
install_dependencies() {
    log_info "Installing dependencies..."
    
    # Upgrade pip first
    log_info "Upgrading pip..."
    if ! $PYTHON_CMD -m pip install --upgrade pip; then
        log_warning "pip upgrade failed, continuing with existing version..."
    fi
    
    # Install requirements
    if [ -f "requirements.txt" ]; then
        log_info "Installing from requirements.txt..."
        if $PYTHON_CMD -m pip install -r requirements.txt; then
            log_success "Dependencies installed successfully"
        else
            log_error "Failed to install some dependencies"
            log_info "Trying to install packages individually..."
            
            # Try installing packages one by one
            packages=(
                "python-telegram-bot==20.7"
                "yookassa==3.7.1" 
                "aiohttp==3.9.1"
                "cryptography==41.0.7"
                "sqlalchemy==2.0.23"
            )
            
            for package in "${packages[@]}"; do
                log_info "Installing $package..."
                if $PYTHON_CMD -m pip install "$package"; then
                    log_success "Installed $package"
                else
                    log_warning "Failed to install $package"
                fi
            done
        fi
    else
        log_error "requirements.txt not found"
        exit 1
    fi
}

# Run the installation script
run_installation() {
    log_info "Running installation script..."
    
    # Set PYTHONPATH to current directory
    export PYTHONPATH=$(pwd):$PYTHONPATH
    
    if $PYTHON_CMD install.py; then
        log_success "Installation completed successfully"
    else
        log_error "Installation failed"
        exit 1
    fi
}

# Set proper permissions
set_permissions() {
    log_info "Setting secure file permissions..."
    
    # Make Python scripts executable
    chmod +x *.py 2>/dev/null || true
    
    # Make sure data directories are writable with secure permissions
    mkdir -p data/vpn_configs data/backups logs
    chmod 755 data data/vpn_configs data/backups logs
    
    # Set secure permissions for sensitive files
    if [ -f "config.ini" ]; then
        chmod 600 config.ini
    fi
    
    if [ -f "data/vpn_bot.db" ]; then
        chmod 600 data/vpn_bot.db
    fi
    
    log_success "Secure permissions set"
}

# Display next steps
show_next_steps() {
    echo ""
    log_success "🎉 Installation completed successfully!"
    echo ""
    echo "📝 Next steps:"
    echo "   1. Review and edit config.ini file with your settings"
    echo "   2. Start the bot with: $PYTHON_CMD bot.py"
    echo "   3. Access admin panel with the credentials you created"
    echo ""
    echo "🔐 Security recommendations:"
    echo "   - Change default passwords regularly"
    echo "   - Keep your server updated"
    echo "   - Monitor logs for suspicious activity"
    echo "   - Regularly backup your database"
    echo ""
    echo "💡 Tips:"
    echo "   - To activate the virtual environment: source venv/bin/activate (Linux/Mac)"
    echo "   - Check the README.md for detailed usage instructions"
    echo ""
}

# Main installation process
main() {
    log_info "Starting VPN Bot Panel installation..."
    
    # Check if not running as root (warning only)
    check_root
    
    # Check and setup repository first
    check_git
    setup_repository
    
    # Check required files
    if ! check_required_files; then
        log_error "Required files are missing even after cloning repository."
        log_info "Please check the repository structure and try again."
        exit 1
    fi
    
    # Check Python
    check_python
    check_python_version
    
    # Create and activate virtual environment
    create_venv
    activate_venv
    
    # Install dependencies
    install_dependencies
    
    # Run installation
    run_installation
    
    # Set permissions
    set_permissions
    
    # Show next steps
    show_next_steps
}

# Run main function
main "$@"