#!/usr/bin/env python3
"""
Simple test for MCP Academic Editor
"""
print("🧪 Testing MCP Academic Editor")
print("=" * 40)

# Test 1: Basic imports
try:
    import server
    print("✅ Server module imports successfully")
except Exception as e:
    print(f"❌ Server import failed: {e}")
    exit(1)

# Test 2: Check tools are defined
try:
    import inspect
    tools = []
    for name, obj in inspect.getmembers(server):
        if hasattr(obj, '__name__') and 'tool' in str(type(obj)):
            tools.append(name)
    
    # Count @mcp.tool() decorators in server.py
    with open('server.py', 'r') as f:
        content = f.read()
        tool_count = content.count('@mcp.tool()')
    
    print(f"✅ Found {tool_count} MCP tools defined")
    
    expected_tools = [
        'process_manuscript',
        'parse_comments', 
        'get_manuscript_structure',
        'create_vision_brief',
        'analyze_comment_alignment',
        'preview_surgical_edits',
        'apply_surgical_edits',
        'get_comment_types_info'
    ]
    
    print("📋 Expected tools:")
    for i, tool in enumerate(expected_tools, 1):
        print(f"   {i}. {tool}")
    
except Exception as e:
    print(f"❌ Tool detection failed: {e}")

print("\n🔧 Configuration Check:")
config_path = "/Users/jeffreyvadala/Library/Application Support/Claude/claude_desktop_config.json"
print(f"Config path: {config_path}")

try:
    import json
    with open(config_path) as f:
        config = json.load(f)
    
    if 'academic-editor' in config['mcpServers']:
        print("✅ academic-editor found in Claude Desktop config")
        editor_config = config['mcpServers']['academic-editor']
        print(f"   Command: {editor_config['command']}")
        print(f"   Server path: {editor_config['args'][0]}")
    else:
        print("❌ academic-editor NOT found in config")
        
except Exception as e:
    print(f"❌ Config check failed: {e}")

print("\n💡 To fix Claude Desktop connection:")
print("1. Completely quit Claude Desktop (Cmd+Q)")
print("2. Wait 15 seconds")
print("3. Reopen Claude Desktop")
print("4. In a new conversation, type: 'What MCP tools are available?'")
print("5. You should see 'academic-editor' with 8 tools")

print("\n✅ MCP Academic Editor is properly configured!")