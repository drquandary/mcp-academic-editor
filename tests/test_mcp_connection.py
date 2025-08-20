#!/usr/bin/env python3
"""
Test MCP Academic Editor server connection and available tools.
"""

import json
import subprocess
import sys

def test_mcp_server():
    """Test that the MCP server responds correctly."""
    try:
        # Test the server with a simple MCP request
        server_path = "/Users/jeffreyvadala/Downloads/modallatour/MCPACADEMICEDITOR/server.py"
        
        # Create an MCP initialize request
        initialize_request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {
                    "name": "test-client",
                    "version": "1.0.0"
                }
            }
        }
        
        print("🔧 Testing MCP Academic Editor server...")
        print(f"📍 Server location: {server_path}")
        print("📡 Sending initialize request...")
        
        # Run server and send request
        process = subprocess.Popen(
            ["python3", server_path],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        # Send initialize request
        request_json = json.dumps(initialize_request) + "\n"
        stdout, stderr = process.communicate(input=request_json, timeout=5)
        
        if stderr:
            print(f"❌ Server stderr: {stderr}")
        
        if stdout:
            print("✅ Server responded!")
            try:
                response = json.loads(stdout.strip())
                if "result" in response:
                    print("✅ MCP initialize successful")
                    print(f"📋 Server capabilities: {response['result']['capabilities']}")
                    return True
                else:
                    print(f"⚠️  Unexpected response: {response}")
                    return False
            except json.JSONDecodeError as e:
                print(f"❌ Failed to parse response: {e}")
                print(f"Raw output: {stdout}")
                return False
        else:
            print("❌ No response from server")
            return False
            
    except subprocess.TimeoutExpired:
        print("❌ Server timed out")
        return False
    except Exception as e:
        print(f"❌ Error testing server: {e}")
        return False
    finally:
        try:
            process.terminate()
        except:
            pass

def verify_claude_config():
    """Verify Claude Desktop configuration."""
    config_path = "/Users/jeffreyvadala/Library/Application Support/Claude/claude_desktop_config.json"
    
    try:
        with open(config_path, 'r') as f:
            config = json.load(f)
        
        if "academic-editor" in config.get("mcpServers", {}):
            print("✅ Academic Editor found in Claude Desktop config")
            server_config = config["mcpServers"]["academic-editor"]
            print(f"📍 Command: {server_config['command']}")
            print(f"📍 Args: {server_config['args']}")
            return True
        else:
            print("❌ Academic Editor not found in Claude Desktop config")
            return False
            
    except Exception as e:
        print(f"❌ Error reading Claude config: {e}")
        return False

if __name__ == "__main__":
    print("=== MCP Academic Editor Connection Test ===\n")
    
    # Test 1: Verify server can start and respond
    server_works = test_mcp_server()
    
    # Test 2: Verify Claude Desktop configuration
    config_works = verify_claude_config()
    
    print("\n=== Results ===")
    if server_works and config_works:
        print("🎉 SUCCESS: MCP Academic Editor is ready for Claude Desktop!")
        print("\n📋 Next Steps:")
        print("1. Restart Claude Desktop app completely")
        print("2. The Academic Editor tools should appear in Claude Desktop")
        print("3. You can now use surgical manuscript editing directly in Claude Desktop!")
        print("\n🔧 Available Tools:")
        print("- process_manuscript: Load and parse manuscripts")  
        print("- parse_comments: Handle any comment format")
        print("- create_vision_brief: Set editing goals")
        print("- preview_surgical_edits: Preview changes before applying")
        print("- apply_surgical_edits: Apply edits with word count protection")
        print("- get_manuscript_structure: Analyze document structure")
        sys.exit(0)
    else:
        print("❌ FAILED: Issues found with MCP Academic Editor setup")
        sys.exit(1)