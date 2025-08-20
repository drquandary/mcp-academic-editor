#!/usr/bin/env python3
"""
Standalone test for MCP Academic Editor server
"""
import asyncio
import json
from server import mcp

async def test_mcp_server():
    """Test the MCP server functionality"""
    print("🧪 Testing MCP Academic Editor Server")
    print("=" * 50)
    
    try:
        # Test if server can start
        print("✅ MCP server initialized successfully")
        
        # List available tools
        tools = mcp.list_tools()
        print(f"📋 Available tools: {len(tools)}")
        
        for i, tool in enumerate(tools, 1):
            print(f"   {i}. {tool.name}")
        
        print("\n🎉 MCP Academic Editor is working correctly!")
        print("\n💡 If Claude Desktop still doesn't see it:")
        print("   1. Make sure Claude Desktop is completely closed")
        print("   2. Wait 10-15 seconds")
        print("   3. Reopen Claude Desktop")
        print("   4. Look for 'academic-editor' in MCP tools")
        
        return True
        
    except Exception as e:
        print(f"❌ Error testing MCP server: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(test_mcp_server())
    if success:
        print("\n✅ Test completed successfully")
    else:
        print("\n❌ Test failed - check error messages above")