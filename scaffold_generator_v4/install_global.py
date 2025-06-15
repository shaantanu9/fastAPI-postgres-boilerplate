#!/usr/bin/env python3
"""
Global Installation Script for Scaffold v4
Makes scaffold v4 available as 'scaffold' command from anywhere
"""

import os
import sys
import shutil
import subprocess
from pathlib import Path


def get_scaffold_root():
    """Get the absolute path to scaffold generator root"""
    return Path(__file__).parent.absolute()


def create_executable_script():
    """Create the main executable script"""
    scaffold_root = get_scaffold_root()
    
    script_content = f'''#!/usr/bin/env python3
"""
Global Scaffold v4 Command
Auto-generated executable script
"""

import sys
import os
from pathlib import Path

# Add scaffold directory to Python path
SCAFFOLD_ROOT = Path("{scaffold_root}")
sys.path.insert(0, str(SCAFFOLD_ROOT))

# Change to scaffold directory for execution
original_cwd = os.getcwd()
os.chdir(SCAFFOLD_ROOT)

try:
    # Import and run main
    from main import main
    main()
except Exception as e:
    print(f"❌ Error running scaffold: {{e}}")
    sys.exit(1)
finally:
    # Restore original directory
    os.chdir(original_cwd)
'''
    
    return script_content


def install_unix_system():
    """Install for Unix-like systems (Linux/macOS)"""
    print("🐧 Installing for Unix-like system...")
    
    script_content = create_executable_script()
    
    # Try multiple installation paths
    install_paths = [
        Path.home() / ".local" / "bin",
        Path("/usr/local/bin"),
        Path.home() / "bin"
    ]
    
    installed = False
    
    for install_path in install_paths:
        try:
            if not install_path.exists():
                install_path.mkdir(parents=True, exist_ok=True)
            
            script_file = install_path / "scaffold"
            script_file.write_text(script_content)
            script_file.chmod(0o755)  # Make executable
            
            print(f"✅ Installed to: {script_file}")
            
            # Check if path is in PATH
            path_env = os.environ.get('PATH', '')
            if str(install_path) in path_env:
                print(f"✅ {install_path} is in PATH")
                installed = True
                break
            else:
                print(f"⚠️ {install_path} not in PATH, trying next location...")
                
        except PermissionError:
            print(f"❌ Permission denied for {install_path}, trying next...")
        except Exception as e:
            print(f"❌ Error installing to {install_path}: {e}")
    
    if not installed:
        # Fallback: install to ~/.local/bin and provide PATH instructions
        fallback_path = Path.home() / ".local" / "bin"
        fallback_path.mkdir(parents=True, exist_ok=True)
        
        script_file = fallback_path / "scaffold"
        script_file.write_text(script_content)
        script_file.chmod(0o755)
        
        print(f"✅ Installed to: {script_file}")
        print(f"⚠️ Please add to your PATH:")
        print(f"   echo 'export PATH=\"$HOME/.local/bin:$PATH\"' >> ~/.bashrc")
        print(f"   echo 'export PATH=\"$HOME/.local/bin:$PATH\"' >> ~/.zshrc")
        print(f"   source ~/.bashrc  # or ~/.zshrc")
        
        installed = True
    
    return installed


def install_windows_system():
    """Install for Windows systems"""
    print("🪟 Installing for Windows system...")
    
    script_content = create_executable_script()
    
    # Create .bat wrapper for Windows
    bat_content = f'''@echo off
python "{get_scaffold_root() / "main.py"}" %*
'''
    
    # Try to install to user Scripts directory
    scripts_dir = Path.home() / "AppData" / "Local" / "Programs" / "Python" / "Scripts"
    
    if not scripts_dir.exists():
        # Alternative location
        scripts_dir = Path.home() / "Scripts"
        scripts_dir.mkdir(exist_ok=True)
    
    try:
        # Install Python script
        script_file = scripts_dir / "scaffold.py"
        script_file.write_text(script_content)
        
        # Install batch file
        bat_file = scripts_dir / "scaffold.bat"
        bat_file.write_text(bat_content)
        
        print(f"✅ Installed to: {scripts_dir}")
        print(f"📄 Python script: {script_file}")
        print(f"📄 Batch file: {bat_file}")
        
        # Check if Scripts is in PATH
        path_env = os.environ.get('PATH', '')
        if str(scripts_dir) not in path_env:
            print(f"⚠️ Please add {scripts_dir} to your PATH environment variable")
        
        return True
        
    except Exception as e:
        print(f"❌ Error installing on Windows: {e}")
        return False


def create_alias_instructions():
    """Provide instructions for creating shell aliases"""
    scaffold_root = get_scaffold_root()
    
    print("\n🔗 Alternative: Shell Alias Setup")
    print("=" * 40)
    
    # Bash/Zsh alias
    print("For Bash/Zsh, add to ~/.bashrc or ~/.zshrc:")
    print(f'alias scaffold="cd {scaffold_root} && python main.py"')
    
    # Fish shell alias
    print("\nFor Fish shell:")
    print(f'alias scaffold "cd {scaffold_root}; and python main.py"')
    
    # PowerShell alias
    print("\nFor PowerShell, add to $PROFILE:")
    print(f'function scaffold {{ cd "{scaffold_root}"; python main.py @args }}')


def create_development_setup():
    """Create development setup with pip install -e"""
    scaffold_root = get_scaffold_root()
    
    print("\n🔧 Development Setup")
    print("=" * 30)
    
    # Create setup.py for pip installation
    setup_content = f'''from setuptools import setup, find_packages

setup(
    name="scaffold-v4",
    version="4.0.0",
    description="FastAPI Scaffold Generator v4 with Auto-Fix",
    packages=find_packages(),
    entry_points={{
        'console_scripts': [
            'scaffold=main:main',
        ],
    }},
    python_requires='>=3.8',
    install_requires=[
        'fastapi',
        'sqlalchemy',
        'alembic',
        'pydantic',
    ],
)
'''
    
    setup_file = scaffold_root / "setup.py"
    setup_file.write_text(setup_content)
    
    print(f"✅ Created setup.py at {setup_file}")
    print("📦 To install in development mode:")
    print(f"   cd {scaffold_root}")
    print("   pip install -e .")
    print("   # Now 'scaffold' command will be available globally")


def test_installation():
    """Test if the scaffold command is working"""
    print("\n🧪 Testing Installation")
    print("=" * 25)
    
    try:
        result = subprocess.run(['scaffold', '--help'], 
                              capture_output=True, text=True, timeout=10)
        
        if result.returncode == 0:
            print("✅ Installation successful!")
            print("🎉 'scaffold' command is working")
            return True
        else:
            print("❌ Command exists but returned error")
            print(f"Error: {result.stderr}")
            return False
            
    except subprocess.TimeoutExpired:
        print("⏱️ Command timed out")
        return False
    except FileNotFoundError:
        print("❌ 'scaffold' command not found in PATH")
        return False
    except Exception as e:
        print(f"❌ Error testing installation: {e}")
        return False


def main():
    """Main installation function"""
    print("🚀 Scaffold v4 Global Installation")
    print("=" * 40)
    
    scaffold_root = get_scaffold_root()
    print(f"📁 Scaffold root: {scaffold_root}")
    
    # Detect operating system
    system = sys.platform.lower()
    
    success = False
    
    if system.startswith('win'):
        success = install_windows_system()
    else:
        success = install_unix_system()
    
    if success:
        print("\n✅ Installation completed!")
        
        # Test the installation
        if test_installation():
            print("\n🎯 Usage Examples:")
            print("  scaffold --help")
            print("  scaffold add Product name:str price:float")
            print("  scaffold auto-fix")
            print("  scaffold list")
        else:
            print("\n⚠️ Installation may need additional setup")
            create_alias_instructions()
    else:
        print("\n❌ Installation failed, providing alternatives...")
        create_alias_instructions()
    
    # Always provide development setup option
    create_development_setup()
    
    print("\n🎉 Setup complete! Try running: scaffold --help")


if __name__ == "__main__":
    main() 