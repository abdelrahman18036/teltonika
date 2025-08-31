#!/bin/bash

# Quick fix to update teltonika command tool with custom command support
# Run on Ubuntu server: bash fix_command_tool.sh

echo "🔧 Updating teltonika command tool..."

# Copy the updated command tool
cp teltonika_updated.sh /usr/local/bin/teltonika
chmod +x /usr/local/bin/teltonika

echo "✅ Teltonika command tool updated!"
echo ""
echo "🧪 Testing API endpoints..."
chmod +x test_api.sh
echo "Run: ./test_api.sh to test API functionality"
echo ""
echo "🚀 Now you can use custom commands:"
echo "   teltonika command"
echo ""
echo "📋 Custom command examples:"
echo "   - getstatus"
echo "   - getver" 
echo "   - setdigout 123"
echo "   - readio"
echo "   - Any Teltonika command"
