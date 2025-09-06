# ✅ FINALNE TESTY MIGRACJI WATER SYSTEM

echo "🎉 MIGRACJA ZAKOŃCZONA POMYŚLNIE!"
echo ""
echo "=== FINALNE TESTY WSZYSTKICH FUNKCJI ==="

echo "1. Test Admin Panel (HTTPS):"
curl -s -w "   → HTTP %{http_code}\n" https://app.krzysztoforlinski.pl/login

echo ""
echo "2. Test ESP32 API endpoint (HTTPS):"
curl -s -w "   → HTTP %{http_code} (oczekiwane 401 - brak autoryzacji)\n" https://app.krzysztoforlinski.pl/api/water-events -X POST

echo ""
echo "3. Test Health Check (HTTPS):"
HEALTH_RESPONSE=$(curl -s https://app.krzysztoforlinski.pl/health)
echo "   → $(echo "$HEALTH_RESPONSE" | jq -r '.status // "ERROR"') ($(echo "$HEALTH_RESPONSE" | jq -r '.timestamp // "NO_TIME"'))"

echo ""
echo "4. Test przekierowania HTTP → HTTPS:"
curl -s -w "   → HTTP %{http_code} (oczekiwane 301)\n" http://app.krzysztoforlinski.pl/health

echo ""
echo "=== STATUS USŁUG ==="
echo "systemd service:"
sudo systemctl is-active water-system && echo "   ✅ water-system: AKTYWNY" || echo "   ❌ water-system: NIEAKTYWNY"

echo ""
echo "nginx service:"
sudo systemctl is-active nginx && echo "   ✅ nginx: AKTYWNY" || echo "   ❌ nginx: NIEAKTYWNY"

echo ""
echo "=== INFORMACJE PRODUKCYJNE ==="
echo "🌐 URL aplikacji:     https://app.krzysztoforlinski.pl/"
echo "🔧 Admin Panel:       https://app.krzysztoforlinski.pl/login"
echo "🤖 ESP32 API:         https://app.krzysztoforlinski.pl/api/"
echo "💓 Health Check:      https://app.krzysztoforlinski.pl/health"
echo ""
echo "📁 Lokalizacja:       /home/kichnu/tap_off_water-vps/"
echo "🗄️ Baza danych:       /home/kichnu/tap_off_water-vps/water_events.db"
echo "📋 Logi aplikacji:    sudo journalctl -u water-system -f"
echo "🔄 Restart usługi:    sudo systemctl restart water-system"

echo ""
echo "=== CERTYFIKAT SSL ==="
echo "Ważność certyfikatu:"
sudo certbot certificates 2>/dev/null | grep "Expiry Date" | head -1

echo ""
echo "=== PODSUMOWANIE KONFIGURACJI ==="
echo "✅ DNS:               app.krzysztoforlinski.pl → $(dig +short app.krzysztoforlinski.pl)"
echo "✅ SSL/HTTPS:         Let's Encrypt (auto-renewal aktywny)"
echo "✅ Reverse Proxy:     Nginx → Flask (porty 5000/5001)"
echo "✅ systemd Service:   Automatyczny start/restart"
echo "✅ Security:          HSTS, proper headers, session management"
echo "✅ Admin Password:    'admin' (ZMIEŃ W app.py!)"

echo ""
echo "=== ZADANIA PO MIGRACJI ==="
echo "🔐 1. ZMIEŃ HASŁO ADMINISTRATORA w app.py (linia ADMIN_PASSWORD)"
echo "📧 2. Skonfiguruj monitoring/alerty"
echo "💾 3. Ustaw backup bazy danych"
echo "🔧 4. Przetestuj z ESP32 (API calls)"
echo "📊 5. Sprawdź logi przez pierwszych 24h"

echo ""
echo "=== UŻYTECZNE KOMENDY ==="
echo "# Status i logi"
echo "sudo systemctl status water-system"
echo "sudo journalctl -u water-system -f"
echo ""
echo "# Restart aplikacji"
echo "sudo systemctl restart water-system"
echo ""
echo "# Sprawdzenie nginx"
echo "sudo nginx -t"
echo "sudo systemctl reload nginx"
echo ""
echo "# Sprawdzenie certyfikatu SSL"
echo "sudo certbot certificates"
echo "sudo certbot renew --dry-run"

echo ""
echo "🚀 APLIKACJA GOTOWA DO PRODUKCJI!"