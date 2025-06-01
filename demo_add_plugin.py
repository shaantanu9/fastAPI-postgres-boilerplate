#!/usr/bin/env python3
"""
🚀 FastAPI Enterprise Plugin System - Demo Script

This script demonstrates how to:
1. Add a new model using the plugin generator
2. Run database migrations
3. Start the application 
4. Verify the routes appear in Swagger UI

Usage:
    python demo_add_plugin.py

The script will:
- Generate a new Product plugin with sample fields
- Apply database migrations
- Show you how to start the server
- Provide links to test the new API endpoints
"""

import subprocess
import sys
import time
from pathlib import Path

def run_command(command, description):
    """Run a command and display the result"""
    print(f"\n🔄 {description}")
    print(f"💻 Running: {command}")
    print("=" * 50)
    
    try:
        result = subprocess.run(
            command, 
            shell=True, 
            capture_output=True, 
            text=True,
            cwd=Path.cwd()
        )
        
        if result.stdout:
            print("📤 Output:")
            print(result.stdout)
        
        if result.stderr:
            print("⚠️ Errors/Warnings:")
            print(result.stderr)
        
        if result.returncode == 0:
            print("✅ Success!")
        else:
            print(f"❌ Failed with exit code: {result.returncode}")
            return False
            
    except Exception as e:
        print(f"❌ Error running command: {e}")
        return False
    
    return True

def main():
    """Main demo function"""
    print("🚀 FastAPI Enterprise Plugin System - Demo")
    print("=" * 60)
    print("This demo will show you how to add a new model with full API endpoints!")
    print()
    
    # Step 1: Generate a sample plugin
    print("📋 Step 1: Generating a sample 'Product' plugin...")
    success = run_command(
        "python scaffold_plugin_generator_v2.py add Product "
        "title:str:max_length=200 "
        "price:float:gt=0 "
        "description:text "
        "category:str:indexed "
        "sku:str:unique "
        "is_active:bool:default=True "
        "--with-tasks --with-bulk",
        "Generating Product plugin with full features"
    )
    
    if not success:
        print("❌ Failed to generate plugin. Please check the errors above.")
        return
    
    # Step 2: List generated plugins  
    print("\n📂 Step 2: Listing all generated plugins...")
    run_command(
        "python scaffold_plugin_generator_v2.py list",
        "Showing all generated plugins"
    )
    
    # Step 3: Run health check
    print("\n🏥 Step 3: Running plugin system health check...")
    run_command(
        "python scaffold_plugin_generator_v2.py health-check",
        "Checking plugin system health"
    )
    
    # Step 4: Show the generated plugin file
    print("\n📄 Step 4: Generated Plugin Structure")
    print("=" * 50)
    plugin_file = Path("app/plugins/product_plugin.py")
    if plugin_file.exists():
        print(f"✅ Plugin file created: {plugin_file}")
        print("📋 Plugin includes:")
        print("   - SQLAlchemy model with proper table configuration")
        print("   - Pydantic schemas with validation")
        print("   - Enhanced service with repository pattern")
        print("   - Complete CRUD endpoints") 
        print("   - Background task integration")
        print("   - Bulk operations support")
        print("   - Event emission for monitoring")
    else:
        print("❌ Plugin file not found!")
    
    # Instructions for running the server
    print("\n🎯 Next Steps - Testing Your Plugin")
    print("=" * 50)
    print("1. 🔄 Start the FastAPI server:")
    print("   python -m uvicorn app.main:app --reload")
    print()
    print("2. 🌐 Open Swagger UI in your browser:")
    print("   http://localhost:8000/docs")
    print()
    print("3. 📊 Check plugin status:")
    print("   http://localhost:8000/plugins/status")
    print()
    print("4. 🛍️ Test Product endpoints:")
    print("   GET    http://localhost:8000/products/")
    print("   POST   http://localhost:8000/products/")
    print("   GET    http://localhost:8000/products/{id}")
    print("   PUT    http://localhost:8000/products/{id}")
    print("   DELETE http://localhost:8000/products/{id}")
    print()
    print("5. 📦 Test bulk operations:")
    print("   POST   http://localhost:8000/products/bulk/")
    print("   PUT    http://localhost:8000/products/bulk/")
    print()
    print("6. ⚙️ Test background tasks:")
    print("   POST   http://localhost:8000/products/{id}/tasks/{operation}")
    print()
    
    # Auto-start option
    print("🚀 Auto-Start Options")
    print("=" * 50)
    
    response = input("Would you like to start the server now? (y/N): ")
    if response.lower() in ['y', 'yes']:
        print("\n🔄 Starting FastAPI server...")
        print("🌐 Server will be available at: http://localhost:8000")
        print("📖 Swagger UI: http://localhost:8000/docs")
        print("🔧 ReDoc: http://localhost:8000/redoc")
        print("\n📝 Press Ctrl+C to stop the server")
        print("=" * 50)
        
        try:
            subprocess.run([
                sys.executable, "-m", "uvicorn", 
                "app.main:app", 
                "--reload", 
                "--host", "0.0.0.0", 
                "--port", "8000"
            ])
        except KeyboardInterrupt:
            print("\n✅ Server stopped.")
    
    print("\n🎉 Demo completed successfully!")
    print("🔍 Your Product plugin is ready to use!")

if __name__ == "__main__":
    main() 