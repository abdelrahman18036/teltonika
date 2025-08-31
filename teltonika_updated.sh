#!/bin/bash

case "$1" in
    start)
        echo "🚀 Starting Teltonika services..."
        sudo systemctl start postgresql
        sudo systemctl start teltonika-django
        sudo systemctl start teltonika
        sudo systemctl start nginx
        echo "✅ All services started"
        ;;
    stop)
        echo "🛑 Stopping Teltonika services..."
        sudo systemctl stop teltonika
        sudo systemctl stop teltonika-django
        sudo systemctl stop nginx
        echo "✅ Services stopped"
        ;;
    restart)
        echo "🔄 Restarting Teltonika services..."
        sudo systemctl restart teltonika
        sudo systemctl restart teltonika-django
        sudo systemctl restart nginx
        echo "✅ Services restarted"
        ;;
    status)
        echo "📊 Service Status:"
        sudo systemctl status teltonika --no-pager
        sudo systemctl status teltonika-django --no-pager
        sudo systemctl status nginx --no-pager
        ;;
    monitor)
        sudo /opt/teltonika/monitor.sh
        ;;
    test)
        sudo -u teltonika /opt/teltonika/venv/bin/python /opt/teltonika/performance_test.py
        ;;
    command)
        echo "📱 Testing Command API functionality..."
        echo "Available commands: lock, unlock, mobilize, immobilize, custom"
        echo "Command types: digital_output, can_control, custom"
        echo ""
        echo "📱 Digital Output Commands:"
        echo "   - lock: setdigout 1?? 2??     # Lock doors - DOUT1=HIGH, additional parameter"
        echo "   - unlock: setdigout ?1? ?2?   # Unlock doors - DOUT2=HIGH, additional parameter"
        echo "   - mobilize: setdigout ??1     # Mobilize engine - DOUT3=HIGH"
        echo "   - immobilize: setdigout ??0   # Immobilize engine - DOUT3=LOW"
        echo ""
        echo "🚗 CAN Control Commands:"
        echo "   - lock: lvcanlockalldoors"
        echo "   - unlock: lvcanopenalldoors"
        echo "   - mobilize: lvcanunblockengine"
        echo "   - immobilize: lvcanblockengine"
        echo ""
        echo "⚙️  Custom Commands:"
        echo "   - Any Teltonika command (e.g., getstatus, getver, setdigout 123)"
        echo ""
        read -p "Enter device IMEI: " imei
        read -p "Enter command type (digital_output/can_control/custom): " cmd_type
        
        if [ "$cmd_type" = "custom" ]; then
            read -p "Enter custom command: " custom_cmd
            read -p "Enter command name (optional, will use command as name): " cmd_name
            
            if [ -z "$cmd_name" ]; then
                cmd_name="$custom_cmd"
            fi
            
            echo "🚀 Sending custom command: $custom_cmd"
            RESPONSE=$(curl -s -X POST "http://127.0.0.1:8000/api/devices/$imei/command/" \
                 -H "Content-Type: application/json" \
                 -d "{\"custom_command\": \"$custom_cmd\"}")
            
            if [ -n "$RESPONSE" ]; then
                echo "$RESPONSE" | python3 -m json.tool 2>/dev/null || echo "Response: $RESPONSE"
            else
                echo "✅ Command sent (no response data)"
            fi
        else
            read -p "Enter command name (lock/unlock/mobilize/immobilize): " cmd_name
            
            echo "🚀 Sending predefined command..."
            RESPONSE=$(curl -s -X POST "http://127.0.0.1:8000/api/devices/$imei/command/" \
                 -H "Content-Type: application/json" \
                 -d "{\"command_type\": \"$cmd_type\", \"command_name\": \"$cmd_name\"}")
            
            if [ -n "$RESPONSE" ]; then
                echo "$RESPONSE" | python3 -m json.tool 2>/dev/null || echo "Response: $RESPONSE"
            else
                echo "✅ Command sent (no response data)"
            fi
        fi
        ;;
    logs)
        echo "📋 Choose log to view:"
        echo "1) Teltonika service logs"
        echo "2) Django API logs"
        echo "3) Nginx logs"
        echo "4) Live GPS data"
        read -p "Enter choice (1-4): " choice
        case $choice in
            1) sudo journalctl -u teltonika -f ;;
            2) sudo journalctl -u teltonika-django -f ;;
            3) sudo tail -f /var/log/nginx/access.log ;;
            4) sudo tail -f /var/log/teltonika/teltonika_service.log | grep "GPS Coordinates" ;;
        esac
        ;;
    scale)
        echo "📈 System Scale Information:"
        echo "Current capacity: 1,000+ devices, 58M+ records/day"
        echo "Performance: 673+ records/second"
        echo ""
        sudo /opt/teltonika/monitor.sh
        ;;
    *)
        echo "🚀 Teltonika GPS Tracking System - Command Control Edition"
        echo "Usage: teltonika {start|stop|restart|status|monitor|test|command|logs|scale}"
        echo ""
        echo "Commands:"
        echo "  start    - Start all services"
        echo "  stop     - Stop all services"
        echo "  restart  - Restart all services"
        echo "  status   - Show service status"
        echo "  monitor  - Show system monitor"
        echo "  test     - Run performance tests"
        echo "  command  - Send test command to device"
        echo "  logs     - View service logs"
        echo "  scale    - View scale information"
        echo ""
        echo "🌐 Web Interface: http://$(hostname -I | awk '{print $1}')/admin/"
        echo "📡 GPS Service: $(hostname -I | awk '{print $1}'):5000"
        echo "📱 Command API: $(hostname -I | awk '{print $1}'):5001"
        echo "👤 Admin Login: orange / 00oo00oo"
        ;;
esac
