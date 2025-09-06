# Krok 1: Backup istniejącego kodu przed migracją credentials

echo "=== BACKUP PRZED MIGRACJĄ CREDENTIALS ==="

# Sprawdź aktualny status git
echo "Status git przed backup:"
git status

echo ""
echo "=== Tworzenie backup commit ==="
# Dodaj wszystkie obecne zmiany
git add -A

# Commit wszystkiego co jest w staging
git commit -m "Backup before credentials migration

- Current working state
- Hardcoded credentials still present
- About to migrate to environment variables"

echo ""
echo "=== Sprawdzenie obecnych credentials w kodzie ==="
echo "Szukanie hardcoded credentials w app.py:"
grep -n "ADMIN_PASSWORD\|VALID_TOKEN" app.py

echo ""
echo "=== Sprawdzenie struktury projektu ==="
ls -la

echo ""
echo "=== Sprawdzenie czy aplikacja obecnie działa ==="
# Sprawdź czy aplikacja działa
ps aux | grep python | grep app.py || echo "Aplikacja nie działa (OK)"

echo ""
echo "✅ Backup utworzony. Możemy kontynuować migrację."
echo ""
echo "NASTĘPNY KROK: Aktualizacja requirements.txt i dodanie python-dotenv"