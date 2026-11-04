#!/bin/bash
# /home/tibo/r/beep-boop/scripts/manage-env.sh
# Environment file management script for beep-boop project
# 
# PURPOSE: Provides safe management of the read-only .env file
# RELATED COMPONENTS: .env, env.example, application configuration
# TAGS: environment, security, configuration, management

set -e

ENV_FILE=".env"
ENV_EXAMPLE="env.example"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to show usage
show_usage() {
    echo "Usage: $0 [COMMAND]"
    echo ""
    echo "Commands:"
    echo "  status     - Show current .env file status and permissions"
    echo "  unlock     - Make .env file writable for editing"
    echo "  lock       - Make .env file read-only (default protection)"
    echo "  backup     - Create a backup of current .env file"
    echo "  restore    - Restore .env from backup"
    echo "  reset      - Reset .env from env.example template"
    echo "  help       - Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0 status          # Check current protection status"
    echo "  $0 unlock          # Allow editing of .env file"
    echo "  $0 lock            # Re-protect .env file after editing"
    echo "  $0 backup          # Create backup before making changes"
}

# Function to check if .env file exists
check_env_exists() {
    if [ ! -f "$PROJECT_ROOT/$ENV_FILE" ]; then
        print_error ".env file not found at $PROJECT_ROOT/$ENV_FILE"
        print_status "Run '$0 reset' to create from template"
        exit 1
    fi
}

# Function to show current status
show_status() {
    cd "$PROJECT_ROOT"
    
    if [ ! -f "$ENV_FILE" ]; then
        print_warning ".env file does not exist"
        return 1
    fi
    
    print_status "Current .env file status:"
    echo "  File: $(pwd)/$ENV_FILE"
    echo "  Permissions: $(ls -la "$ENV_FILE" | awk '{print $1}')"
    echo "  Size: $(du -h "$ENV_FILE" | cut -f1)"
    echo "  Modified: $(stat -c %y "$ENV_FILE")"
    
    # Check if file is read-only
    if [ ! -w "$ENV_FILE" ]; then
        print_success ".env file is PROTECTED (read-only)"
    else
        print_warning ".env file is UNPROTECTED (writable)"
    fi
}

# Function to unlock .env file for editing
unlock_env() {
    cd "$PROJECT_ROOT"
    check_env_exists
    
    print_status "Making .env file writable for editing..."
    chmod 644 "$ENV_FILE"
    print_success ".env file is now writable"
    print_warning "Remember to run '$0 lock' after editing to re-protect the file"
}

# Function to lock .env file (make read-only)
lock_env() {
    cd "$PROJECT_ROOT"
    check_env_exists
    
    print_status "Making .env file read-only for protection..."
    chmod 444 "$ENV_FILE"
    print_success ".env file is now protected (read-only)"
}

# Function to create backup
backup_env() {
    cd "$PROJECT_ROOT"
    check_env_exists
    
    local backup_name=".env.backup.$(date +%Y%m%d_%H%M%S)"
    print_status "Creating backup: $backup_name"
    cp "$ENV_FILE" "$backup_name"
    print_success "Backup created: $backup_name"
}

# Function to restore from backup
restore_env() {
    cd "$PROJECT_ROOT"
    
    # Find the most recent backup
    local latest_backup=$(ls -t .env.backup.* 2>/dev/null | head -n1)
    
    if [ -z "$latest_backup" ]; then
        print_error "No backup files found (.env.backup.*)"
        exit 1
    fi
    
    print_status "Restoring from backup: $latest_backup"
    cp "$latest_backup" "$ENV_FILE"
    chmod 444 "$ENV_FILE"  # Re-protect after restore
    print_success "Restored from backup and re-protected"
}

# Function to reset .env from template
reset_env() {
    cd "$PROJECT_ROOT"
    
    if [ ! -f "$ENV_EXAMPLE" ]; then
        print_error "Template file $ENV_EXAMPLE not found"
        exit 1
    fi
    
    print_status "Resetting .env from $ENV_EXAMPLE template..."
    cp "$ENV_EXAMPLE" "$ENV_FILE"
    chmod 444 "$ENV_FILE"  # Make it read-only immediately
    print_success ".env file reset from template and protected"
    print_warning "Remember to update the values in .env with your actual credentials"
}

# Main script logic
main() {
    case "${1:-help}" in
        "status")
            show_status
            ;;
        "unlock")
            unlock_env
            ;;
        "lock")
            lock_env
            ;;
        "backup")
            backup_env
            ;;
        "restore")
            restore_env
            ;;
        "reset")
            reset_env
            ;;
        "help"|"-h"|"--help")
            show_usage
            ;;
        *)
            print_error "Unknown command: $1"
            echo ""
            show_usage
            exit 1
            ;;
    esac
}

# Run main function with all arguments
main "$@"
