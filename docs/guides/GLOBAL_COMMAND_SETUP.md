# Global Command Setup for Scaffold v4

This guide shows you how to run `scaffold` from anywhere in your system without having to navigate to the `scaffold_generator_v4` directory.

## Quick Setup Options

### Option 1: Automatic Installation (Recommended)

Run the automatic installer:

```bash
cd /path/to/fastAPI_PostGres/scaffold_generator_v4
python install_global.py
```

This will:

- Create a global `scaffold` command
- Install it to your system PATH
- Test the installation
- Provide fallback options if needed

### Option 2: Manual Shell Script Setup (Unix/Linux/macOS)

1. Make the script executable:

```bash
cd /path/to/fastAPI_PostGres/scaffold_generator_v4
chmod +x scaffold
```

2. Add to your PATH by creating a symlink:

```bash
# Create symlink in a directory that's in your PATH
sudo ln -s $(pwd)/scaffold /usr/local/bin/scaffold

# Or for user-only installation:
mkdir -p ~/.local/bin
ln -s $(pwd)/scaffold ~/.local/bin/scaffold

# Add to PATH if not already there
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc
```

### Option 3: Manual Batch File Setup (Windows)

1. Add the scaffold directory to your PATH:

   - Open System Properties → Advanced → Environment Variables
   - Add the full path to `scaffold_generator_v4` to your PATH variable
   - Or copy `scaffold.bat` to a directory already in PATH

2. Test by opening Command Prompt and running:

```cmd
scaffold --help
```

### Option 4: Shell Alias (Quick & Easy)

Add an alias to your shell configuration:

**For Bash/Zsh** (`~/.bashrc` or `~/.zshrc`):

```bash
alias scaffold="cd /path/to/fastAPI_PostGres/scaffold_generator_v4 && python main.py"
```

**For Fish** (`~/.config/fish/config.fish`):

```fish
alias scaffold "cd /path/to/fastAPI_PostGres/scaffold_generator_v4; and python main.py"
```

**For PowerShell** (`$PROFILE`):

```powershell
function scaffold { cd "C:\path\to\fastAPI_PostGres\scaffold_generator_v4"; python main.py @args }
```

### Option 5: Development Installation with pip

1. Create a development installation:

```bash
cd /path/to/fastAPI_PostGres/scaffold_generator_v4
pip install -e .
```

2. Now `scaffold` will be available globally as a Python package.

## Usage Examples

Once installed, you can run scaffold from anywhere:

```bash
# Check help
scaffold --help

# Generate a new model from any directory
scaffold add Product name:str price:float:gt=0 status:str:choices=active,inactive

# Auto-fix migration issues
scaffold auto-fix

# List existing plugins
scaffold list

# Check system health
scaffold health-check

# Quick migration health check
scaffold migration-health

# Test enhanced features
scaffold test-enhanced
```

## Verification

Test your installation:

```bash
# Should show help text
scaffold --help

# Should show version and available commands
scaffold list

# Should show system status
scaffold health-check
```

## Troubleshooting

### Command Not Found

If you get "command not found" error:

1. **Check PATH**: Ensure the installation directory is in your PATH
2. **Restart Terminal**: Close and reopen your terminal
3. **Check Permissions**: Ensure the script is executable (`chmod +x`)
4. **Use Full Path**: Try running with full path to verify it works

### Permission Errors

If you get permission errors:

```bash
# Fix script permissions
chmod +x /path/to/scaffold_generator_v4/scaffold

# For system-wide installation, use sudo
sudo ln -s /path/to/scaffold_generator_v4/scaffold /usr/local/bin/scaffold
```

### Python Path Issues

If you get Python import errors:

1. Ensure you're running from the correct directory internally
2. The scripts automatically handle path changes
3. Try the pip installation method instead

### Windows-Specific Issues

1. **Execution Policy**: You may need to update PowerShell execution policy:

   ```powershell
   Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
   ```

2. **Python Command**: Use `python` instead of `python3` on Windows

3. **Path Separators**: Ensure you're using Windows path format in batch files

## Advanced: Multiple Environment Setup

If you have multiple scaffold installations:

```bash
# Create environment-specific commands
ln -s /path/to/project1/scaffold_generator_v4/scaffold ~/.local/bin/scaffold-dev
ln -s /path/to/project2/scaffold_generator_v4/scaffold ~/.local/bin/scaffold-prod

# Use specific versions
scaffold-dev add Model field:type    # For development
scaffold-prod add Model field:type   # For production
```

## Uninstallation

To remove the global command:

```bash
# Remove symlink
sudo rm /usr/local/bin/scaffold
# or
rm ~/.local/bin/scaffold

# Remove alias (edit your shell config file)
# Remove from ~/.bashrc, ~/.zshrc, etc.

# Uninstall pip package
pip uninstall scaffold-v4
```

## Benefits of Global Command

✅ **Run from anywhere**: No need to navigate to scaffold directory
✅ **Consistent interface**: Same command structure everywhere  
✅ **Integration friendly**: Works with CI/CD, scripts, and automation
✅ **Development efficiency**: Faster workflow for model generation
✅ **Team consistency**: Everyone uses the same command format

## Examples in Different Directories

```bash
# From your home directory
cd ~
scaffold add User name:str email:email

# From a project directory
cd /some/other/project
scaffold auto-fix
scaffold add Order total:float status:str:choices=pending,complete

# From anywhere
scaffold health-check
scaffold list
```

The global command automatically handles directory changes internally, so all scaffold operations work correctly regardless of your current working directory.
